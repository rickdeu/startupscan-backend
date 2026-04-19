import logging
import os
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from startupscan_api.roles import ROLE_ADMIN, ROLE_ANALISTA, get_user_role
from startupscan_api.services.model_registry import (
    get_active_model_name,
    get_meta_path,
    get_metrics_path,
    get_model_path,
    set_active_model,
)
from .helpers import (
    _list_available_models,
    _read_json_file,
    _safe_slug_model_name,
    _write_json_file,
)
from .jobs import _model_training_cache_key, _start_model_training_job
from .mixins import RoleRequiredMixin

logger = logging.getLogger(__name__)


class ModelManagementView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_ANALISTA, ROLE_ADMIN}

    def get(self, request):
        models = _list_available_models()
        active_job_id = request.GET.get("job_id", "").strip()
        active_job = cache.get(_model_training_cache_key(active_job_id)) if active_job_id else None
        context = {
            "models": models,
            "active_model": get_active_model_name(),
            "enhanced_available": (
                (Path(settings.DATA_DIR) / "pitches_dataset_enhanced.csv").exists()
                and (Path(settings.DATA_DIR) / "financials_dataset_enhanced.csv").exists()
            ),
            "active_job_id": active_job_id,
            "active_job": active_job or {},
        }
        return render(request, "analyzer/model_management.html", context)

    def post(self, request):
        action = request.POST.get("action", "").strip()
        user_role = get_user_role(request.user)
        admin_only_actions = {"set_active", "save_meta", "delete"}
        if user_role != ROLE_ADMIN and action in admin_only_actions:
            messages.error(
                request,
                "Ação restrita ao administrador. O perfil Analista não pode editar, ativar ou deletar modelos.",
            )
            return redirect("model_management")

        try:
            if action == "fetch_external":
                job_id = _start_model_training_job(action="fetch_external")
                messages.success(request, "Importação de dataset iniciada. Acompanhe o progresso em tempo real.")
                return redirect(f"{request.path}?job_id={job_id}")

            elif action == "train_new":
                model_name_raw = request.POST.get("model_name", "").strip()
                if not model_name_raw:
                    raise ValueError("Nome do modelo é obrigatório para novo treino.")
                dataset_source = request.POST.get("dataset_source", "default")
                normalized_name = _safe_slug_model_name(model_name_raw)
                job_id = _start_model_training_job(
                    action="train_new",
                    model_name=model_name_raw,
                    dataset_source=dataset_source,
                )
                messages.success(request, f"Treino do novo modelo iniciado: {normalized_name}")
                return redirect(f"{request.path}?job_id={job_id}")

            elif action == "retrain":
                model_name = request.POST.get("model_name", "")
                dataset_source = request.POST.get("dataset_source", "default")
                if not model_name:
                    raise ValueError("Modelo não informado para retreino.")
                job_id = _start_model_training_job(
                    action="retrain",
                    model_name=model_name,
                    dataset_source=dataset_source,
                )
                messages.success(request, f"Retreino iniciado para: {model_name}")
                return redirect(f"{request.path}?job_id={job_id}")

            elif action == "set_active":
                model_name = request.POST.get("model_name", "")
                if not model_name:
                    raise ValueError("Modelo não informado para ativação.")
                if not get_model_path(model_name).exists():
                    raise FileNotFoundError(f"Modelo não encontrado: {model_name}")
                set_active_model(model_name)
                messages.success(request, f"Modelo ativo atualizado para: {model_name}")

            elif action == "save_meta":
                model_name = request.POST.get("model_name", "")
                display_name = request.POST.get("display_name", "").strip()
                description = request.POST.get("description", "").strip()
                if not model_name:
                    raise ValueError("Modelo não informado para edição.")
                meta_path = get_meta_path(model_name)
                payload = _read_json_file(meta_path)
                payload["display_name"] = display_name
                payload["description"] = description
                _write_json_file(meta_path, payload)
                messages.success(request, f"Metadados atualizados para {model_name}.")

            elif action == "delete":
                model_name = request.POST.get("model_name", "")
                if not model_name:
                    raise ValueError("Modelo não informado para exclusão.")

                available = _list_available_models()
                if len(available) <= 1:
                    raise ValueError("Não é possível excluir o único modelo disponível.")

                for file_path in [get_model_path(model_name), get_metrics_path(model_name), get_meta_path(model_name)]:
                    try:
                        if Path(file_path).exists():
                            os.remove(file_path)
                    except OSError:
                        pass

                if get_active_model_name() == model_name:
                    remaining = _list_available_models()
                    if remaining:
                        set_active_model(remaining[0]["name"])

                messages.success(request, f"Modelo removido: {model_name}")

            else:
                messages.error(request, "Ação inválida no painel de modelos.")

        except Exception as exc:
            logger.error("Model management action failed: %s", str(exc), exc_info=True)
            messages.error(request, f"Falha ao executar ação: {str(exc)}")

        return redirect("model_management")


class ModelTrainingProgressView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_ANALISTA, ROLE_ADMIN}

    def get(self, request, job_id):
        state = cache.get(_model_training_cache_key(job_id))
        if not state:
            return JsonResponse({"error": "Job não encontrado"}, status=404)
        return JsonResponse(state, status=200)
