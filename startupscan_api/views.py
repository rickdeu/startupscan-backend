import os
import json
import logging
import tempfile
import threading
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.contrib import messages
from django.contrib.auth import login
from startupscan_api.forms import RegisterForm
from startupscan_api.models import IdeaPitchSubmission, PitchAnalysis
from startupscan_api.services.model_training import (
    ensure_model_exists,
    predict_pitch_score,
    train_model_task,
)
from startupscan_api.modeling import analyze_with_gpt, ensure_report_dict, train_and_evaluate
from startupscan_api.util.file_management import TempFileManager
from startupscan_api.services.model_registry import (
    get_active_model_name,
    get_meta_path,
    get_metrics_path,
    get_model_path,
    set_active_model,
)
from startupscan_api.services.pitch_input import extract_text_from_uploaded_file, merge_pitch_text
from startupscan_api.services.report_export import export_analysis_pdf
from startupscan_api.services.pitch_builder import (
    PITCH_DESIGN_MODE_AUTO,
    export_pitch_pdf,
    generate_pitch_from_idea,
    get_pitch_design_mode_choices,
    get_pitch_design_template_choices,
    normalize_pitch_design_options,
)
from startupscan_api.services.pitch_video import (
    build_did_presenter_source_urls,
    generate_explainer_video,
)

import joblib
from celery.result import AsyncResult
from django.core.management import call_command
from django.core.cache import cache
from django.db import close_old_connections
from django.db.models import Avg, Count, Max
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import FileResponse, JsonResponse

from .utils import (
    prepare_features,
    generate_interpretable_report
)

logger = logging.getLogger(__name__)


def _safe_exception_message(exc: Exception, max_len: int = 280) -> str:
    """Normaliza mensagem de erro para exibição no frontend/API."""
    raw = str(exc).strip() or exc.__class__.__name__
    lower = raw.lower()

    if "no module named" in lower:
        normalized = f"Dependência ausente no servidor: {raw}"
    elif "permission denied" in lower:
        normalized = f"Permissão negada ao acessar ficheiros: {raw}"
    elif "file is not a zip file" in lower:
        normalized = "Ficheiro inválido/corrompido. Reenvie o anexo e tente novamente."
    elif "cannot identify image file" in lower:
        normalized = "Não foi possível ler a imagem enviada. Use JPG ou PNG válidos."
    elif "ffmpeg" in lower:
        normalized = f"Falha no processamento de mídia (ffmpeg): {raw}"
    else:
        normalized = raw

    if len(normalized) > max_len:
        normalized = normalized[: max_len - 3].rstrip() + "..."
    return normalized


def _infer_error_field(error_text: str) -> str:
    text = (error_text or "").strip().lower()
    if not text:
        return "general"

    if any(k in text for k in ("áudio", "audio", "whisper", "mfcc")):
        return "audio_file"
    if any(k in text for k in ("vídeo", "video", "ffmpeg", "mediapipe", "deepface")):
        return "video_file"
    if "youtube" in text:
        return "youtube_url"
    if any(k in text for k in ("documento", "document", "docx", "pdf", "txt", "csv", "ficheiro", "arquivo")):
        return "text_file"
    if any(k in text for k in ("receita", "revenue")):
        return "revenue"
    if any(k in text for k in ("crescimento", "growth")):
        return "growth_rate"
    if any(k in text for k in ("margem", "profit_margin")):
        return "profit_margin"
    if any(k in text for k in ("modelo", "openai", "gpt")):
        return "model_source"
    if any(k in text for k in ("e-mail", "email")):
        return "contact_email"
    if "startup" in text:
        return "startup_name"
    return "general"


def _safe_slug_model_name(raw_name):
    name = (raw_name or "").strip().lower()
    sanitized = []
    for ch in name:
        if ch.isalnum() or ch in {"-", "_"}:
            sanitized.append(ch)
        else:
            sanitized.append("-")
    cleaned = "".join(sanitized).strip("-_")
    if not cleaned:
        cleaned = "pitch-model"
    if not cleaned.endswith(".pkl"):
        cleaned = f"{cleaned}.pkl"
    return cleaned


def _resolve_pitch_design_selection(request, *, default_mode: str | None = None, default_template: str | None = None):
    mode = (request.GET.get("design_mode", "") or "").strip().lower() or (default_mode or PITCH_DESIGN_MODE_AUTO)
    template = (request.GET.get("design_template", "") or "").strip().lower() or (default_template or "")
    return normalize_pitch_design_options(mode, template)


def _read_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json_file(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _list_available_models():
    os.makedirs(settings.AI_MODELS_DIR, exist_ok=True)
    active_model = get_active_model_name()
    models = []

    for file_path in sorted(Path(settings.AI_MODELS_DIR).glob("*.pkl")):
        model_name = file_path.name
        metrics = _read_json_file(get_metrics_path(model_name))
        meta = _read_json_file(get_meta_path(model_name))
        consistency = metrics.get("consistency_accuracy_pct")
        cv_r2 = metrics.get("cv_r2")
        models.append(
            {
                "name": model_name,
                "display_name": meta.get("display_name", model_name.replace(".pkl", "").replace("-", " ").title()),
                "description": meta.get("description", ""),
                "is_active": model_name == active_model,
                "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime),
                "metrics": metrics,
                "consistency_accuracy_pct": consistency if consistency is not None else None,
                "cv_r2_pct": round(float(cv_r2) * 100, 2) if cv_r2 is not None else None,
            }
        )
    return models


def _run_training_for_model(model_name, dataset_source="default"):
    model_path = get_model_path(model_name)
    cmd_args = ["--model-output", str(model_path)]

    if dataset_source == "enhanced":
        pitches = Path(settings.DATA_DIR) / "pitches_dataset_enhanced.csv"
        financials = Path(settings.DATA_DIR) / "financials_dataset_enhanced.csv"
        if pitches.exists() and financials.exists():
            cmd_args.extend(["--pitches-data", str(pitches), "--financials-data", str(financials)])

    call_command("train_model", *cmd_args)
    return model_path


MODEL_TRAINING_CACHE_PREFIX = "model_training_job"
MODEL_TRAINING_TTL_SECONDS = 60 * 60 * 24
VIDEO_GENERATION_CACHE_PREFIX = "explainer_video_job"
VIDEO_GENERATION_TTL_SECONDS = 60 * 60 * 24


def _model_training_cache_key(job_id: str) -> str:
    return f"{MODEL_TRAINING_CACHE_PREFIX}:{job_id}"


def _video_generation_cache_key(job_id: str) -> str:
    return f"{VIDEO_GENERATION_CACHE_PREFIX}:{job_id}"


def _write_model_training_state(job_id: str, **updates):
    key = _model_training_cache_key(job_id)
    state = cache.get(key) or {
        "job_id": job_id,
        "status": "PENDING",
        "progress": 0,
        "message": "Aguardando início do treino",
    }
    state.update(updates)
    state["updated_at"] = timezone.now().isoformat()
    cache.set(key, state, MODEL_TRAINING_TTL_SECONDS)
    return state


def _write_video_generation_state(job_id: str, **updates):
    key = _video_generation_cache_key(job_id)
    state = cache.get(key) or {
        "job_id": job_id,
        "status": "PENDING",
        "progress": 0,
        "phase": "fila",
        "message": "Aguardando início da geração de vídeo",
    }
    state.update(updates)
    state["updated_at"] = timezone.now().isoformat()
    cache.set(key, state, VIDEO_GENERATION_TTL_SECONDS)
    return state


def _run_explainer_video_job(
    job_id: str,
    analysis_id: int,
    presenter_path: str | None = None,
    presenter_url: str | None = None,
    presenter_source_urls: list[str] | None = None,
    generation_mode: str = "auto",
):
    temp_output = None
    try:
        close_old_connections()
        _write_video_generation_state(
            job_id,
            status="RUNNING",
            progress=8,
            phase="inicializacao",
            message="Inicializando geração do vídeo explicativo",
            analysis_id=analysis_id,
            generation_mode=generation_mode,
        )

        analysis = PitchAnalysis.objects.get(id=analysis_id)

        media_root = settings.MEDIA_ROOT
        try:
            os.makedirs(media_root, exist_ok=True)
        except OSError:
            media_root = os.path.join(settings.BASE_DIR, "media")
            os.makedirs(media_root, exist_ok=True)

        temp_dir = os.path.join(media_root, "generated_videos")
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_output = os.path.join(temp_dir, f"explainer_{analysis.id}_{timestamp}.mp4")

        _write_video_generation_state(
            job_id,
            status="RUNNING",
            progress=24,
            phase="preparacao",
            message="Preparando recursos visuais e áudio",
        )

        _write_video_generation_state(
            job_id,
            status="RUNNING",
            progress=35,
            phase="renderizacao",
            message="Criando roteiro executivo e iniciando renderização",
        )

        def _video_progress_callback(progress_pct: int, phase: str, message: str):
            bounded = max(35, min(94, int(progress_pct)))
            _write_video_generation_state(
                job_id,
                status="RUNNING",
                progress=bounded,
                phase=phase or "renderizacao",
                message=message or "Processando vídeo...",
            )

        video_meta = generate_explainer_video(
            analysis,
            temp_output,
            presenter_image_path=presenter_path,
            presenter_image_url=presenter_url,
            presenter_source_urls=presenter_source_urls or [],
            generation_mode=generation_mode,
            progress_callback=_video_progress_callback,
        )

        _write_video_generation_state(
            job_id,
            status="RUNNING",
            progress=78,
            phase="persistencia",
            message="Salvando vídeo no resultado da análise",
        )
        final_name = f"explainer_{analysis.id}.mp4"
        with open(temp_output, "rb") as fh:
            analysis.explainer_video_file.save(final_name, File(fh), save=False)

        metadata = analysis.metadata or {}
        metadata["explainer_video"] = video_meta
        metadata["explainer_video_job_id"] = job_id
        metadata["explainer_video_job_status"] = "COMPLETED"
        metadata["explainer_video_mode"] = generation_mode
        metadata.pop("explainer_video_job_error", None)
        analysis.metadata = metadata
        analysis.save(update_fields=["explainer_video_file", "metadata", "updated_at"])

        _write_video_generation_state(
            job_id,
            status="COMPLETED",
            progress=100,
            phase="concluido",
            message="Vídeo explicativo gerado com sucesso",
            result={
                "analysis_id": analysis_id,
                "video_url": analysis.explainer_video_file.url if analysis.explainer_video_file else "",
                "generation_mode": generation_mode,
            },
        )
    except Exception as exc:
        logger.error("Falha no job de vídeo explicativo: %s", str(exc), exc_info=True)
        error_detail = str(exc).strip() or exc.__class__.__name__
        did_status = getattr(exc, "did_status", None)
        did_error = getattr(exc, "did_error", None)
        local_error = getattr(exc, "local_error", None)
        try:
            analysis = PitchAnalysis.objects.get(id=analysis_id)
            metadata = analysis.metadata or {}
            metadata["explainer_video_job_id"] = job_id
            metadata["explainer_video_job_status"] = "FAILED"
            metadata["explainer_video_mode"] = generation_mode
            metadata["explainer_video_job_error"] = error_detail
            explainer_video_meta = metadata.get("explainer_video")
            if not isinstance(explainer_video_meta, dict):
                explainer_video_meta = {}
            explainer_video_meta.update(
                {
                    "status": "failed",
                    "error": error_detail,
                    "generated_at": timezone.now().isoformat(),
                }
            )
            if did_status:
                explainer_video_meta["did_status"] = did_status
            if did_error:
                explainer_video_meta["did_error"] = did_error
            if local_error:
                explainer_video_meta["local_error"] = local_error
            metadata["explainer_video"] = explainer_video_meta
            analysis.metadata = metadata
            analysis.save(update_fields=["metadata", "updated_at"])
        except Exception:
            pass
        _write_video_generation_state(
            job_id,
            status="FAILED",
            progress=100,
            phase="falha",
            message=f"Falha ao gerar vídeo: {error_detail[:220]}",
            error=error_detail,
            did_status=did_status,
            did_error=did_error,
            local_error=local_error,
            analysis_id=analysis_id,
            generation_mode=generation_mode,
        )
    finally:
        if temp_output:
            try:
                if os.path.exists(temp_output):
                    os.remove(temp_output)
            except OSError:
                pass
        close_old_connections()


def _start_explainer_video_job(
    analysis: PitchAnalysis,
    presenter_path: str | None = None,
    presenter_url: str | None = None,
    presenter_source_urls: list[str] | None = None,
    generation_mode: str = "auto",
) -> str:
    job_id = str(uuid.uuid4())
    _write_video_generation_state(
        job_id,
        status="PENDING",
        progress=0,
        phase="fila",
        message="Job de vídeo criado, aguardando execução",
        analysis_id=analysis.id,
        generation_mode=generation_mode,
    )
    thread = threading.Thread(
        target=_run_explainer_video_job,
        kwargs={
            "job_id": job_id,
            "analysis_id": analysis.id,
            "presenter_path": presenter_path,
            "presenter_url": presenter_url,
            "presenter_source_urls": presenter_source_urls or [],
            "generation_mode": generation_mode,
        },
        daemon=True,
    )
    thread.start()
    return job_id


def _normalize_model_name(raw_model_name: str, action: str) -> str:
    raw_model_name = (raw_model_name or "").strip()
    if action == "train_new":
        return _safe_slug_model_name(raw_model_name)
    if raw_model_name.endswith(".pkl"):
        return raw_model_name
    return _safe_slug_model_name(raw_model_name)


def _run_model_training_job(job_id: str, action: str, model_name: str = "", dataset_source: str = "default"):
    try:
        _write_model_training_state(job_id, status="RUNNING", progress=5, message="Inicializando job de treino")

        if action == "fetch_external":
            _write_model_training_state(job_id, progress=15, message="Importando dataset externo")
            call_command("fetch_external_dataset", "--combine-with-default", "--output-prefix", "enhanced")
            _write_model_training_state(
                job_id,
                status="COMPLETED",
                progress=100,
                message="Dataset externo importado com sucesso",
                result={"action": "fetch_external"},
            )
            return

        normalized_model_name = _normalize_model_name(model_name, action)
        model_path = get_model_path(normalized_model_name)
        _write_model_training_state(job_id, progress=12, message=f"Preparando treino para {normalized_model_name}")

        if dataset_source == "enhanced":
            pitches_path = Path(settings.DATA_DIR) / "pitches_dataset_enhanced.csv"
            financials_path = Path(settings.DATA_DIR) / "financials_dataset_enhanced.csv"
            if not pitches_path.exists() or not financials_path.exists():
                _write_model_training_state(job_id, progress=18, message="Dataset enhanced não encontrado; usando padrão")
                pitches_path = Path(settings.DATA_DIR) / "pitches_dataset.csv"
                financials_path = Path(settings.DATA_DIR) / "financials_dataset.csv"
        else:
            pitches_path = Path(settings.DATA_DIR) / "pitches_dataset.csv"
            financials_path = Path(settings.DATA_DIR) / "financials_dataset.csv"

        _write_model_training_state(job_id, progress=20, message="Carregando datasets para treino")
        pitches_df = pd.read_csv(pitches_path)
        financial_df = pd.read_csv(financials_path)

        def _progress_callback(progress_pct, message):
            bounded = max(20, min(95, int(progress_pct)))
            _write_model_training_state(job_id, status="RUNNING", progress=bounded, message=message)

        _write_model_training_state(job_id, progress=25, message="Treinamento iniciado")
        model_bundle, metrics = train_and_evaluate(
            pitches_df,
            financial_df,
            progress_callback=_progress_callback,
        )

        _write_model_training_state(job_id, progress=96, message="Salvando modelo e métricas")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model_bundle, model_path)
        _write_json_file(get_metrics_path(normalized_model_name), metrics)

        if action == "train_new":
            set_active_model(normalized_model_name)

        _write_model_training_state(
            job_id,
            status="COMPLETED",
            progress=100,
            message=f"Treino concluído para {normalized_model_name}",
            result={
                "model_name": normalized_model_name,
                "metrics": metrics,
                "action": action,
            },
        )
    except Exception as exc:
        _write_model_training_state(
            job_id,
            status="FAILED",
            progress=100,
            message=f"Falha no treino: {str(exc)}",
            error=str(exc),
        )


def _start_model_training_job(action: str, model_name: str = "", dataset_source: str = "default") -> str:
    job_id = str(uuid.uuid4())
    _write_model_training_state(
        job_id,
        status="PENDING",
        progress=0,
        message="Job criado, aguardando execução",
        action=action,
        model_name=model_name,
        dataset_source=dataset_source,
    )
    thread = threading.Thread(
        target=_run_model_training_job,
        kwargs={
            "job_id": job_id,
            "action": action,
            "model_name": model_name,
            "dataset_source": dataset_source,
        },
        daemon=True,
    )
    thread.start()
    return job_id


class StartupPitchAnalyzer(APIView):
    """
    Endpoint para análise multimodal de pitches de startups
    """
    
    def post(self, request):
        try:
            # Extrair dados da requisição
            text = request.data.get('text', '')
            text_file = request.FILES.get('text_file')
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            youtube_url = (request.data.get("youtube_url", "") or "").strip()
            startup_name = (request.data.get("startup_name", "") or "").strip()
            industry = (request.data.get("industry", "") or "").strip()
            financial_data = request.data.get('financial_data', {})
            model_source = str(request.data.get("model_source", "local")).strip().lower()
            if model_source not in {"local", "gpt"}:
                model_source = "local"

            extracted_text = extract_text_from_uploaded_file(text_file)
            text = merge_pitch_text(text, extracted_text, youtube_url)
            if not text:
                return Response(
                    {"error": "Pitch text not provided. Send text or upload a document."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # 2. Processar arquivos temporários (context manager recomendado)
            with TempFileManager(audio_file, video_file) as file_paths:
                audio_path, video_path = file_paths
                
                # 3. Preparar dados para análise
                pitch_data = {
                    'text': text,
                    'audio_path': audio_path,
                    'video_path': video_path,
                    'youtube_url': youtube_url,
                }
                
                # 4. Extrair features
                features, metadata = prepare_features(pitch_data, financial_data)
                metadata["analysis_engine_requested"] = model_source
                metadata["startup_name"] = startup_name
                metadata["industry"] = industry
                metadata["analysis_context_id"] = str(uuid.uuid4())

                prediction = None
                report = None
                engine_used = model_source

                # 5. Fazer previsão por GPT quando solicitado
                if model_source == "gpt":
                    prediction, report, engine_used = analyze_with_gpt(text, financial_data, metadata)

                # 6. Fallback para modelo local treinado
                if prediction is None:
                    model = ensure_model_exists()
                    if model is None:
                        return Response(
                            {'error': 'Model not available and could not be trained'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE
                        )
                    prediction = predict_pitch_score(
                        model=model,
                        pitch_data=pitch_data,
                        financial_data=financial_data,
                        precomputed_features=features,
                    )
                    report = generate_interpretable_report(prediction, metadata)
                    engine_used = "local"

                report = ensure_report_dict(report, prediction)
                metadata["analysis_engine_used"] = engine_used
                metadata["sources"] = {
                    "text_file_name": text_file.name if text_file else "",
                    "youtube_url": youtube_url,
                    "has_audio": bool(audio_file),
                    "has_video": bool(video_file),
                }
                
                return Response({
                    'success_score': float(prediction),
                    'category_scores': report.get("category_scores", {}),
                    'report': report,
                    'metadata': metadata,
                    'engine_used': engine_used,
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing pitch: {str(e)}", exc_info=True)
            detail = _safe_exception_message(e)
            return Response(
                {'error': f'An error occurred during analysis: {detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





class ModelRetrainView(APIView):
    """Endpoint apenas para disparar o retreinamento em background"""
    
    def post(self, request):
        try:
            # Execução síncrona no ambiente atual.
            result = train_model_task()
            task_id = result.get("task_id") if isinstance(result, dict) else None

            return Response(
                {
                    "message": "Model training executed",
                    "task_id": task_id,
                    "result": result,
                    "status_endpoint": f"/training/status/{task_id}/" if task_id else None
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




class TrainingStatusView(APIView):
    """Endpoint para verificar status do treinamento"""
    
    def get(self, request, task_id):
        try:
            if not task_id or str(task_id).lower() in {"none", "null"}:
                return Response(
                    {
                        "task_id": task_id,
                        "status": "COMPLETED",
                        "ready": True,
                        "result": {"message": "Training was executed synchronously"}
                    },
                    status=status.HTTP_200_OK
                )

            task = AsyncResult(task_id)
            
            response = {
                "task_id": task.id,
                "status": task.status,
                "ready": task.ready()
            }
            
            if task.failed():
                response["error"] = str(task.result)
            elif task.successful():
                response["result"] = task.result
                
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("Training status backend unavailable for task %s: %s", task_id, str(e))
            return Response(
                {
                    "task_id": task_id,
                    "status": "UNAVAILABLE",
                    "ready": False,
                    "error": "Task backend unavailable in current runtime"
                },
                status=status.HTTP_200_OK
            )





import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.conf import settings
import uuid
import os
from .tasks import process_batch_analysis
from .serializers import BatchAnalysisSerializer

class BatchAnalysisView(APIView):
    """Endpoint para análise em lote de múltiplos pitches"""
    
    def post(self, request):
        try:
            # 1. Validar entrada
            serializer = BatchAnalysisSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['file']
            
            # 2. Criar ID único para o lote
            batch_id = str(uuid.uuid4())
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'batch_analysis')
            os.makedirs(temp_dir, exist_ok=True)
            
            # 3. Salvar arquivo temporário
            temp_file_path = os.path.join(temp_dir, f"{batch_id}.csv")
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            cache_key = f'batch_analysis:{batch_id}'
            # 4. Armazenar metadados iniciais no cache (expira em 24h)
            cache.set(cache_key, {
                'status': 'PENDING',
                'total_items': 0,
                'processed_items': 0,
                'results_file': None,
                'task_id': None
            }, 86400)  # 24 horas

            # 5. Iniciar tarefa assíncrona, com fallback síncrono sem broker
            execution_mode = "async"
            try:
                task = process_batch_analysis.delay(temp_file_path, batch_id)
            except Exception:
                logger.warning(
                    "Celery broker unavailable. Running batch analysis synchronously.",
                    exc_info=True
                )
                execution_mode = "sync"
                task = process_batch_analysis.apply(args=[temp_file_path, batch_id])

            status_data = cache.get(cache_key) or {}
            status_data['task_id'] = getattr(task, 'id', None)
            cache.set(cache_key, status_data, 86400)
            
            return Response({
                'batch_id': batch_id,
                'status_url': f'/batch/status/{batch_id}/',
                'message': 'Batch analysis started',
                'mode': execution_mode
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchAnalysisStatusView(APIView):
    """Endpoint para verificar status do processamento em lote"""
    
    def get(self, request, batch_id):
        try:
            cache_key = f'batch_analysis:{batch_id}'
            status_data = cache.get(cache_key)
            
            if not status_data:
                return Response(
                    {'error': 'Batch ID not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(status_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchAnalysisResultsView(APIView):
    """Endpoint para download dos resultados"""
    
    def get(self, request, batch_id):
        try:
            cache_key = f'batch_analysis:{batch_id}'
            status_data = cache.get(cache_key)
            
            if not status_data or status_data['status'] != 'COMPLETED':
                return Response(
                    {'error': 'Results not ready'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            results_path = status_data['results_file']
            
            if not os.path.exists(results_path):
                return Response(
                    {'error': 'Results file missing'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Retornar o arquivo para download
            with open(results_path, 'rb') as fh:
                response = Response(fh.read(), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="batch_results_{batch_id}.csv"'
                return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardView(View):
    """Dashboard inicial"""
    def get(self, request):
        try:
            min_score = float(request.GET.get("min_score", 0) or 0)
        except ValueError:
            min_score = 0.0
        try:
            max_score = float(request.GET.get("max_score", 10) or 10)
        except ValueError:
            max_score = 10.0
        try:
            days = int(request.GET.get("days", 90) or 90)
        except ValueError:
            days = 90
        engine = str(request.GET.get("engine", "all")).strip().lower()
        if engine not in {"all", "local", "gpt"}:
            engine = "all"

        min_score = max(0.0, min(10.0, min_score))
        max_score = max(0.0, min(10.0, max_score))
        if max_score < min_score:
            max_score = min_score

        all_scored = PitchAnalysis.objects.exclude(success_score__isnull=True)
        if days > 0:
            all_scored = all_scored.filter(created_at__gte=timezone.now() - timedelta(days=days))
        if engine != "all":
            all_scored = all_scored.filter(metadata__analysis_engine_requested=engine)
        all_scored = all_scored.filter(success_score__gte=min_score, success_score__lte=max_score)

        if not request.user.is_authenticated:
            recent_analyses = PitchAnalysis.objects.none()
        else:
            recent_qs = (
                PitchAnalysis.objects.filter(user=request.user, success_score__isnull=False)
                .filter(success_score__gte=min_score, success_score__lte=max_score)
            )
            if engine != "all":
                recent_qs = recent_qs.filter(metadata__analysis_engine_requested=engine)
            recent_analyses = recent_qs.order_by('-created_at')[:8]
            
        global_stats = all_scored.aggregate(
            avg_score=Avg("success_score"),
            total=Count("id"),
            best=Max("success_score"),
        )
        models = _list_available_models()
        active_model = next((m for m in models if m["is_active"]), None)

        history = list(all_scored.order_by("-created_at")[:24])
        history.reverse()
        chart_labels = [f"#{item.id}" for item in history]
        chart_ids = [item.id for item in history]
        chart_scores = [float(item.success_score or 0) for item in history]
        chart_revenues = [float(item.revenue or 0) for item in history]
        chart_growth = [float(item.growth_rate or 0) for item in history]
        score_distribution = [
            all_scored.filter(success_score__lt=5).count(),
            all_scored.filter(success_score__gte=5, success_score__lt=7.5).count(),
            all_scored.filter(success_score__gte=7.5).count(),
        ]

        industry_labels_map = dict(PitchAnalysis.INDUSTRY_CHOICES)
        sector_rows = list(
            all_scored.values("industry").annotate(avg_score=Avg("success_score"), total=Count("id")).order_by("-avg_score")
        )
        sector_labels = [industry_labels_map.get(row["industry"], row["industry"]) for row in sector_rows]
        sector_avg_scores = [round(float(row["avg_score"] or 0), 2) for row in sector_rows]
        sector_totals = [int(row["total"] or 0) for row in sector_rows]

        user_sector_comparison = {}
        if request.user.is_authenticated and recent_analyses:
            latest = recent_analyses[0]
            sector_avg = all_scored.filter(industry=latest.industry).aggregate(avg=Avg("success_score")).get("avg") or 0
            user_sector_comparison = {
                "industry_label": industry_labels_map.get(latest.industry, latest.industry),
                "latest_score": round(float(latest.success_score or 0), 2),
                "sector_avg": round(float(sector_avg), 2),
            }
        
        return render(request, 'analyzer/dashboard.html', {
            'recent_analyses': recent_analyses,
            'global_stats': global_stats,
            'active_model': active_model,
            'models_count': len(models),
            'chart_labels_json': json.dumps(chart_labels),
            'chart_ids_json': json.dumps(chart_ids),
            'chart_scores_json': json.dumps(chart_scores),
            'chart_revenues_json': json.dumps(chart_revenues),
            'chart_growth_json': json.dumps(chart_growth),
            'chart_distribution_json': json.dumps(score_distribution),
            'chart_sector_labels_json': json.dumps(sector_labels),
            'chart_sector_avg_json': json.dumps(sector_avg_scores),
            'chart_sector_total_json': json.dumps(sector_totals),
            'filter_min_score': min_score,
            'filter_max_score': max_score,
            'filter_days': days,
            'filter_engine': engine,
            'user_sector_comparison': user_sector_comparison,
        })


class IdeaPitchBuilderView(View):
    """
    Formulário simplificado para guardar ideia no banco.
    """

    required_fields = {
        "startup_name": "Nome da startup",
        "problem": "Problema",
        "solution": "Solução",
        "target_customer": "Cliente-alvo",
        "business_model": "Modelo de negócio",
    }

    @staticmethod
    def _collect_form_data(request):
        form_data = {
            "startup_name": request.POST.get("startup_name", "").strip(),
            "one_liner": request.POST.get("one_liner", "").strip(),
            "problem": request.POST.get("problem", "").strip(),
            "solution": request.POST.get("solution", "").strip(),
            "target_customer": request.POST.get("target_customer", "").strip(),
            "market_size": request.POST.get("market_size", "").strip(),
            "business_model": request.POST.get("business_model", "").strip(),
            "competitive_advantage": request.POST.get("competitive_advantage", "").strip(),
            "traction": request.POST.get("traction", "").strip(),
            "team": request.POST.get("team", "").strip(),
            "funding_goal": request.POST.get("funding_goal", "").strip(),
            "use_of_funds": request.POST.get("use_of_funds", "").strip(),
            "call_to_action": request.POST.get("call_to_action", "").strip(),
            "model_source": request.POST.get("model_source", "local").strip().lower(),
        }
        if form_data["model_source"] not in {"local", "gpt"}:
            form_data["model_source"] = "local"
        return form_data

    def _validate(self, form_data):
        errors = {}
        for field, label in self.required_fields.items():
            if not form_data.get(field):
                errors[field] = f"{label} é obrigatório."
        return errors

    def get(self, request):
        context = {
            "form_data": {"model_source": "local"},
            "errors": {},
        }
        return render(request, "analyzer/idea_pitch_form.html", context)

    def post(self, request):
        form_data = self._collect_form_data(request)
        errors = self._validate(form_data)

        if errors:
            messages.error(request, "Preencha os campos obrigatórios para guardar a ideia.")
            return render(request, "analyzer/idea_pitch_form.html", {"form_data": form_data, "errors": errors})

        try:
            submission = IdeaPitchSubmission.objects.create(
                user=request.user if request.user.is_authenticated else None,
                startup_name=form_data["startup_name"],
                one_liner=form_data["one_liner"],
                problem=form_data["problem"],
                solution=form_data["solution"],
                target_customer=form_data["target_customer"],
                market_size=form_data["market_size"],
                business_model=form_data["business_model"],
                competitive_advantage=form_data["competitive_advantage"],
                traction=form_data["traction"],
                team=form_data["team"],
                funding_goal=form_data["funding_goal"],
                use_of_funds=form_data["use_of_funds"],
                call_to_action=form_data["call_to_action"],
                model_source=form_data["model_source"],
            )
            messages.success(
                request,
                "Informações guardadas com sucesso. Revise os dados e clique em 'Gerar Pitch Completo'.",
            )
            return redirect("idea_pitch_detail", submission_id=submission.id)
        except Exception as exc:
            logger.error("Falha ao guardar submissão de ideia: %s", str(exc), exc_info=True)
            messages.error(request, "Não foi possível guardar a ideia. Tente novamente.")
            return render(request, "analyzer/idea_pitch_form.html", {"form_data": form_data, "errors": {}})


class IdeaPitchDetailView(View):
    """
    Página de revisão da ideia guardada + ação de gerar pitch completo.
    """

    @staticmethod
    def _can_access(request, submission):
        if submission.user_id and request.user.is_authenticated:
            return submission.user_id == request.user.id
        if submission.user_id and not request.user.is_authenticated:
            return False
        return True

    @staticmethod
    def _to_payload(submission):
        return {
            "startup_name": submission.startup_name,
            "one_liner": submission.one_liner,
            "problem": submission.problem,
            "solution": submission.solution,
            "target_customer": submission.target_customer,
            "market_size": submission.market_size,
            "business_model": submission.business_model,
            "competitive_advantage": submission.competitive_advantage,
            "traction": submission.traction,
            "team": submission.team,
            "funding_goal": submission.funding_goal,
            "use_of_funds": submission.use_of_funds,
            "call_to_action": submission.call_to_action,
        }

    def get(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        if not self._can_access(request, submission):
            return redirect("dashboard")

        design_template_choices = get_pitch_design_template_choices()
        selected_design_mode, selected_design_template = _resolve_pitch_design_selection(
            request,
            default_mode=PITCH_DESIGN_MODE_AUTO,
            default_template=(design_template_choices[0][0] if design_template_choices else "orbit"),
        )
        context = {
            "submission": submission,
            "generated_pitch": submission.generated_pitch if submission.status == "generated" else {},
            "pitch_design_mode_choices": get_pitch_design_mode_choices(),
            "pitch_design_template_choices": design_template_choices,
            "selected_pitch_design_mode": selected_design_mode,
            "selected_pitch_design_template": selected_design_template,
        }
        return render(request, "analyzer/idea_pitch_detail.html", context)

    def post(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        if not self._can_access(request, submission):
            return redirect("dashboard")

        action = request.POST.get("action", "generate").strip().lower()
        if action != "generate":
            return redirect("idea_pitch_detail", submission_id=submission.id)

        try:
            pitch_payload = generate_pitch_from_idea(
                self._to_payload(submission),
                model_source=submission.model_source,
            )
            submission.generated_pitch = pitch_payload
            submission.status = "generated"
            submission.generated_at = timezone.now()
            submission.save(update_fields=["generated_pitch", "status", "generated_at", "updated_at"])
            messages.success(request, "Pitch completo gerado com sucesso. Já está pronto para apresentação.")
        except Exception as exc:
            logger.error("Falha ao gerar pitch completo: %s", str(exc), exc_info=True)
            messages.error(request, "Não foi possível gerar o pitch completo. Tente novamente.")

        return redirect("idea_pitch_detail", submission_id=submission.id)


class IdeaPitchPDFView(View):
    """
    Exporta PDF do pitch completo a partir da submissão guardada.
    """

    def get(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        if submission.user_id and request.user.is_authenticated and submission.user_id != request.user.id:
            return redirect("dashboard")
        if submission.user_id and not request.user.is_authenticated:
            return redirect("login")

        if submission.status != "generated" or not submission.generated_pitch:
            payload = {
                "startup_name": submission.startup_name,
                "one_liner": submission.one_liner,
                "problem": submission.problem,
                "solution": submission.solution,
                "target_customer": submission.target_customer,
                "market_size": submission.market_size,
                "business_model": submission.business_model,
                "competitive_advantage": submission.competitive_advantage,
                "traction": submission.traction,
                "team": submission.team,
                "funding_goal": submission.funding_goal,
                "use_of_funds": submission.use_of_funds,
                "call_to_action": submission.call_to_action,
            }
            generated = generate_pitch_from_idea(payload, model_source=submission.model_source)
            submission.generated_pitch = generated
            submission.status = "generated"
            submission.generated_at = timezone.now()
            submission.save(update_fields=["generated_pitch", "status", "generated_at", "updated_at"])

        media_root = settings.MEDIA_ROOT
        try:
            os.makedirs(media_root, exist_ok=True)
        except OSError:
            media_root = os.path.join(settings.BASE_DIR, "media")
            os.makedirs(media_root, exist_ok=True)

        target_dir = os.path.join(media_root, "idea_pitches")
        os.makedirs(target_dir, exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in submission.startup_name).strip("_").lower()
        safe_name = safe_name or "startup"
        output_path = os.path.join(
            target_dir,
            f"pitch_{safe_name}_{submission.id}.pdf",
        )
        design_mode, design_template = _resolve_pitch_design_selection(
            request,
            default_mode=PITCH_DESIGN_MODE_AUTO,
            default_template="orbit",
        )
        export_pitch_pdf(
            submission.generated_pitch,
            output_path,
            design_mode=design_mode,
            manual_template=design_template,
        )

        return FileResponse(
            open(output_path, "rb"),
            as_attachment=True,
            filename=f"pitch_completo_{safe_name}.pdf",
            content_type="application/pdf",
        )


class PitchFormView(View):
    """Formulário para análise de pitch com tratamento completo de erros"""
    
    def get(self, request):
        """Exibe o formulário vazio"""
        context = {
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50,  # MB
            'industries': PitchAnalysis.INDUSTRY_CHOICES,
            'form_data': {'model_source': 'local'},
        }
        return render(request, 'analyzer/pitch_form.html', context)

    def post(self, request):
        """Processa o formulário submetido"""
        try:
            # 1. Validação inicial dos dados obrigatórios
            startup_name = request.POST.get("startup_name", "").strip()
            contact_email = request.POST.get("contact_email", "").strip()
            industry = request.POST.get("industry", "tech").strip() or "tech"

            raw_text = request.POST.get('text', '').strip()
            text_file = request.FILES.get("text_file")
            youtube_url = request.POST.get("youtube_url", "").strip()
            extracted_text = extract_text_from_uploaded_file(text_file)
            text = merge_pitch_text(raw_text, extracted_text, youtube_url)

            if not text or len(text) < 100:
                messages.error(request, "O texto do pitch deve ter pelo menos 100 caracteres.", extra_tags="text:Texto muito curto")
                return self._render_form_with_data(request)

            if text_file:
                allowed = (".txt", ".md", ".csv", ".pdf", ".docx")
                lower_name = (text_file.name or "").lower()
                if not lower_name.endswith(allowed):
                    messages.error(
                        request,
                        "Documento de texto inválido. Use TXT, MD, CSV, PDF ou DOCX.",
                        extra_tags="text_file:Formato inválido",
                    )
                    return self._render_form_with_data(request)

            # Na validação do áudio
            # 2. Validação dos arquivos
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            if audio_file:
                if not self._is_valid_audio(audio_file):
                    messages.error(request, "Formato de áudio inválido. Use MP3, WAV ou OGG.", extra_tags="audio_file:Formato inválido")
                    return self._render_form_with_data(request)
                
                if audio_file.size > 50 * 1024 * 1024:
                    messages.error(request, "O arquivo de áudio não pode exceder 50MB.", extra_tags="audio_file:Tamanho excedido")
                    return self._render_form_with_data(request)

            # Na validação do vídeo
            if video_file:
                if not self._is_valid_video(video_file):
                    messages.error(request, "Formato de vídeo inválido. Use MP4, MOV ou AVI.", extra_tags="video_file:Formato inválido")
                    return self._render_form_with_data(request)
                
                if video_file.size > 100 * 1024 * 1024:
                    messages.error(request, "O arquivo de vídeo não pode exceder 100MB.", extra_tags="video_file:Tamanho excedido")
                    return self._render_form_with_data(request)

            if youtube_url and not youtube_url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
                messages.error(
                    request,
                    "Link do YouTube inválido.",
                    extra_tags="youtube_url:URL inválida"
                )
                return self._render_form_with_data(request)

            if not video_file and not youtube_url:
                # vídeo é opcional, mas indicamos na UX quando nenhum envio de vídeo existe
                pass
           
           
           
            # 3. Validação dos dados financeiros
            try:
                financial_data = {
                    'revenue': float(request.POST.get('revenue', 0)),
                    'growth_rate': float(request.POST.get('growth_rate', 0)),
                    'profit_margin': float(request.POST.get('profit_margin', 0))
                }
                
                if financial_data['revenue'] < 0:
                    raise ValueError("Receita não pode ser negativa")
                if not (-100 <= financial_data['growth_rate'] <= 1000):
                    raise ValueError("Taxa de crescimento deve estar entre -100% e 1000%")
                if not (0 <= financial_data['profit_margin'] <= 100):
                    raise ValueError("Margem de lucro deve estar entre 0% e 100%")
                    
            except ValueError as e:
                detail = f"Dados financeiros inválidos: {str(e)}"
                field = _infer_error_field(detail)
                messages.error(request, detail, extra_tags=f"{field}:{detail}")
                return self._render_form_with_data(request)
            
            # 4. Estratégia de análise escolhida pelo usuário
            model_source = str(request.POST.get("model_source", "local")).strip().lower()
            if model_source not in {"local", "gpt"}:
                model_source = "local"

            model = None
            if model_source == "local":
                model = ensure_model_exists()
                if model is None:
                    logger.critical("Modelo de análise não disponível")
                    return render(request, 'analyzer/error.html', {
                        'error': 'Sistema temporariamente indisponível. Por favor, tente mais tarde.'
                    }, status=503)
            
            # 5. Processamento dos arquivos temporários
            try:
                with self._create_temp_file_manager(audio_file, video_file) as file_paths:
                    audio_path, video_path = file_paths
                    
                    # 6. Preparação dos dados para análise
                    pitch_data = {
                        'text': text,
                        'audio_path': audio_path,
                        'video_path': video_path,
                        'youtube_url': youtube_url,
                        'submission_date': request.POST.get('submission_date')
                    }
                    
                    # 7. Extração de features
                    features, metadata = prepare_features(pitch_data, financial_data)
                    
                    metadata["analysis_engine_requested"] = model_source
                    metadata["startup_name"] = startup_name
                    metadata["industry"] = industry
                    metadata["analysis_context_id"] = str(uuid.uuid4())
                    prediction = None
                    report = None
                    engine_used = model_source

                    # 8. Realização da predição com GPT (quando solicitado)
                    if model_source == "gpt":
                        prediction, report, engine_used = analyze_with_gpt(text, financial_data, metadata)

                    # 9. Fallback local para garantir resposta consistente
                    if prediction is None:
                        if model is None:
                            model = ensure_model_exists()
                        if model is None:
                            raise RuntimeError("Modelo local indisponível para fallback")

                        prediction = predict_pitch_score(
                            model=model,
                            pitch_data=pitch_data,
                            financial_data=financial_data,
                            precomputed_features=features,
                        )
                        report = generate_interpretable_report(prediction, metadata)
                        engine_used = "local"

                    prediction = max(0, min(10, float(prediction)))  # Garante score entre 0-10
                    report = ensure_report_dict(report, prediction)
                    metadata["analysis_engine_used"] = engine_used
                    metadata["sources"] = {
                        "text_file_name": text_file.name if text_file else "",
                        "youtube_url": youtube_url,
                        "has_audio": bool(audio_file),
                        "has_video": bool(video_file),
                    }
                     
                    # 10. Salvamento da análise
                    analysis = self._save_analysis(
                        request=request,
                        startup_name=startup_name,
                        industry=industry,
                        contact_email=contact_email,
                        text=text,
                        text_file=text_file,
                        audio_file=audio_file,
                        video_file=video_file,
                        financial_data=financial_data,
                        prediction=prediction,
                        report=report,
                        metadata=metadata
                    )
                    
                    # 11. Redirecionamento para resultados
                    return redirect('pitch_results', analysis_id=analysis.id)
                    
            except Exception as e:
                logger.error(f"Erro durante processamento: {str(e)}", exc_info=True)
                detail = _safe_exception_message(e)
                field = _infer_error_field(detail)
                user_msg = f"Erro durante o processamento: {detail}"
                messages.error(request, user_msg, extra_tags=f"{field}:{user_msg}")
                return self._render_form_with_data(request)
                
        except Exception as e:
            logger.critical(f"Erro inesperado: {str(e)}", exc_info=True)
            detail = _safe_exception_message(e)
            field = _infer_error_field(detail)
            user_msg = f"Erro inesperado na validação: {detail}"
            messages.error(request, user_msg, extra_tags=f"{field}:{user_msg}")
            return self._render_form_with_data(request)

    # Métodos auxiliares
    def _is_valid_audio(self, audio_file):
        """Valida o formato do arquivo de áudio"""
        valid_extensions = ['.mp3', '.wav', '.ogg', '.webm', '.m4a']
        ext = os.path.splitext(audio_file.name)[1].lower()
        return ext in valid_extensions

    def _is_valid_video(self, video_file):
        """Valida o formato do arquivo de vídeo"""
        valid_extensions = ['.mp4', '.mov', '.avi', '.webm']
        ext = os.path.splitext(video_file.name)[1].lower()
        return ext in valid_extensions

    def _create_temp_file_manager(self, audio_file, video_file):
        """Cria gerenciador de arquivos temporários"""
        class TempFileManager:
            def __init__(self, audio, video):
                self.audio = audio
                self.video = video
                self.audio_path = None
                self.video_path = None
            
            def __enter__(self):
                fs = FileSystemStorage(location=tempfile.gettempdir())
                if self.audio:
                    audio_ext = os.path.splitext(self.audio.name)[1].lower() or ".bin"
                    self.audio_path = fs.save(f"pitch_audio_{tempfile.gettempprefix()}{audio_ext}", self.audio)
                if self.video:
                    video_ext = os.path.splitext(self.video.name)[1].lower() or ".bin"
                    self.video_path = fs.save(f"pitch_video_{tempfile.gettempprefix()}{video_ext}", self.video)
                return (self.audio_path, self.video_path)
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                fs = FileSystemStorage(location=tempfile.gettempdir())
                if self.audio_path and fs.exists(self.audio_path):
                    fs.delete(self.audio_path)
                if self.video_path and fs.exists(self.video_path):
                    fs.delete(self.video_path)
        
        return TempFileManager(audio_file, video_file)

    def _save_analysis(self, request, startup_name, industry, contact_email, text, text_file, audio_file, video_file, 
                      financial_data, prediction, report, metadata):
        """Salva a análise no banco de dados"""
        valid_industries = {choice[0] for choice in PitchAnalysis.INDUSTRY_CHOICES}
        if industry not in valid_industries:
            industry = "other"

        return PitchAnalysis.objects.create(
            user=request.user if request.user.is_authenticated else None,
            startup_name=startup_name or None,
            industry=industry,
            contact_email=contact_email or None,
            text=text,
            document_file=text_file,
            audio_file=audio_file,
            video_file=video_file,
            revenue=financial_data['revenue'],
            growth_rate=financial_data['growth_rate'],
            profit_margin=financial_data['profit_margin'],
            success_score=float(prediction),
            report=report,
            metadata=metadata,
            ip_address=self._get_client_ip(request)
        )

    def _get_client_ip(self, request):
        """Obtém o IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')


    def _render_form_with_data(self, request):
        """Re-renderiza o formulário com os dados submetidos e mensagens de erro"""
        form_data = {
            'startup_name': request.POST.get('startup_name', ''),
            'industry': request.POST.get('industry', 'tech'),
            'contact_email': request.POST.get('contact_email', ''),
            'text': request.POST.get('text', ''),
            'youtube_url': request.POST.get('youtube_url', ''),
            'revenue': request.POST.get('revenue', ''),
            'growth_rate': request.POST.get('growth_rate', ''),
            'profit_margin': request.POST.get('profit_margin', ''),
            'model_source': request.POST.get('model_source', 'local'),
            'text_file': request.FILES.get('text_file'),
            'audio_file': request.FILES.get('audio'),
            'video_file': request.FILES.get('video')
        }
        
        # Extrair erros das mensagens
        errors = {}
        general_errors = []
        storage = messages.get_messages(request)
        for message in storage:
            msg_text = str(message)
            if hasattr(message, "extra_tags") and message.extra_tags and ":" in message.extra_tags:
                field, error_msg = message.extra_tags.split(":", 1)
                field = (field or "general").strip()
                if field == "general":
                    general_errors.append(error_msg.strip() or msg_text)
                else:
                    errors[field] = (error_msg.strip() or msg_text)
            else:
                general_errors.append(msg_text)
        
        context = {
            'form_data': form_data,
            'errors': errors,
            'general_errors': general_errors,
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50,  # MB
            'industries': PitchAnalysis.INDUSTRY_CHOICES,
        }
        return render(request, 'analyzer/pitch_form.html', context)

class PitchResultsView(View):
    """Página de resultados da análise"""
    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        last_pitch_meta = (analysis.metadata or {}).get("last_generated_pitch_payload", {})
        if not isinstance(last_pitch_meta, dict):
            last_pitch_meta = {}
        selected_video_mode = str((analysis.metadata or {}).get("explainer_video_mode", "auto") or "auto").strip().lower()
        if selected_video_mode not in {"auto", "did_only", "local_only"}:
            selected_video_mode = "auto"
        design_template_choices = get_pitch_design_template_choices()
        selected_pitch_design_mode, selected_pitch_design_template = _resolve_pitch_design_selection(
            request,
            default_mode=str(last_pitch_meta.get("design_mode", PITCH_DESIGN_MODE_AUTO)),
            default_template=str(last_pitch_meta.get("design_template", design_template_choices[0][0] if design_template_choices else "orbit")),
        )
        active_video_job_id = (request.GET.get("video_job_id", "") or "").strip()
        if not active_video_job_id:
            active_video_job_id = str((analysis.metadata or {}).get("explainer_video_job_id", "") or "").strip()
        active_video_job = None
        if active_video_job_id:
            state = cache.get(_video_generation_cache_key(active_video_job_id))
            if (
                state
                and int(state.get("analysis_id") or 0) == int(analysis.id)
                and str(state.get("status", "")).upper() in {"PENDING", "RUNNING"}
            ):
                active_video_job = state
        return render(request, 'analyzer/result.html', {
            'analysis': analysis,
            'active_video_job_id': active_video_job_id,
            'active_video_job': active_video_job or {},
            'selected_video_mode': selected_video_mode,
            'pitch_design_mode_choices': get_pitch_design_mode_choices(),
            'pitch_design_template_choices': design_template_choices,
            'selected_pitch_design_mode': selected_pitch_design_mode,
            'selected_pitch_design_template': selected_pitch_design_template,
        })


def _build_pitch_payload_from_analysis(analysis: PitchAnalysis) -> dict:
    report = analysis.report or {}
    investor_pitch = report.get("investor_pitch", {}) if isinstance(report, dict) else {}
    strengths = report.get("strengths", []) if isinstance(report, dict) else []
    weaknesses = report.get("weaknesses", []) if isinstance(report, dict) else []
    recommendations = report.get("recommendations", []) if isinstance(report, dict) else []
    summary = str(report.get("summary", "") if isinstance(report, dict) else "").strip()

    startup_name = analysis.startup_name or f"Startup {analysis.id}"
    industry_label = analysis.get_industry_display() if hasattr(analysis, "get_industry_display") else (analysis.industry or "mercado")
    one_liner = summary.split(".")[0].strip() if summary else f"{startup_name} resolve problemas críticos no setor {industry_label}."

    def _join_list(values, fallback):
        values = values if isinstance(values, list) else []
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        return " ".join(cleaned[:3]) if cleaned else fallback

    revenue = float(analysis.revenue or 0)
    growth_rate = float(analysis.growth_rate or 0)
    profit_margin = float(analysis.profit_margin or 0)
    success_score = float(analysis.success_score or 0)

    funding_goal_aoa = max(8_000_000, int(max(revenue * 0.55, 0)))
    funding_goal = f"AOA {funding_goal_aoa:,.0f} para acelerar escala e execução comercial."

    return {
        "startup_name": startup_name,
        "one_liner": one_liner,
        "problem": _join_list(
            weaknesses,
            f"Baixa eficiência e oportunidade de modernização no setor {industry_label}.",
        ),
        "solution": _join_list(
            strengths,
            "Solução com foco em eficiência operacional, crescimento e previsibilidade de resultados.",
        ),
        "target_customer": f"Empresas e decisores estratégicos no setor {industry_label}.",
        "market_size": investor_pitch.get("investment_thesis", "") or "Mercado em expansão com espaço para liderança regional.",
        "business_model": (
            "Modelo orientado a geração de receita recorrente e expansão comercial disciplinada."
        ),
        "competitive_advantage": _join_list(
            strengths,
            "Execução rápida, leitura de métricas e adaptação contínua ao mercado.",
        ),
        "traction": (
            f"Score {success_score:.1f}/10, receita AOA {revenue:,.0f}, "
            f"crescimento {growth_rate:.1f}% e margem {profit_margin:.1f}%."
        ),
        "team": "Equipe focada em execução e melhoria contínua com orientação a metas de crescimento.",
        "funding_goal": investor_pitch.get("suggested_ticket", "") or funding_goal,
        "use_of_funds": _join_list(
            investor_pitch.get("capital_use_plan", []),
            "Produto, aquisição de clientes e fortalecimento da operação para escala.",
        ),
        "call_to_action": _join_list(
            recommendations,
            "Proposta para avançar para reunião de investimento com plano de execução detalhado.",
        ),
    }


class PitchReportPDFView(View):
    """Exporta relatório de análise em PDF."""

    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        if analysis.user and request.user.is_authenticated and analysis.user_id != request.user.id:
            return redirect("dashboard")

        media_root = settings.MEDIA_ROOT
        try:
            os.makedirs(media_root, exist_ok=True)
        except OSError:
            media_root = os.path.join(settings.BASE_DIR, "media")
            os.makedirs(media_root, exist_ok=True)

        reports_dir = os.path.join(media_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"analysis_report_{analysis.id}.pdf")
        export_analysis_pdf(analysis, output_path)

        return FileResponse(
            open(output_path, "rb"),
            as_attachment=True,
            filename=f"relatorio_pitch_{analysis.id}.pdf",
            content_type="application/pdf",
        )


class PitchInvestorPDFView(View):
    """Gera PDF de pitch (com slides) a partir da avaliação da startup."""

    def get(self, request, analysis_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if analysis.user and request.user.is_authenticated and analysis.user_id != request.user.id:
            return redirect("dashboard")

        try:
            payload = _build_pitch_payload_from_analysis(analysis)
            model_source = (request.GET.get("model_source", "") or "").strip().lower()
            if model_source not in {"local", "gpt"}:
                model_source = "gpt" if os.getenv("OPENAI_API_KEY") else "local"
            design_mode, design_template = _resolve_pitch_design_selection(
                request,
                default_mode=PITCH_DESIGN_MODE_AUTO,
                default_template="orbit",
            )

            pitch_payload = generate_pitch_from_idea(payload, model_source=model_source)

            media_root = settings.MEDIA_ROOT
            try:
                os.makedirs(media_root, exist_ok=True)
            except OSError:
                media_root = os.path.join(settings.BASE_DIR, "media")
                os.makedirs(media_root, exist_ok=True)

            pitch_dir = os.path.join(media_root, "analysis_pitches")
            os.makedirs(pitch_dir, exist_ok=True)
            startup_name = analysis.startup_name or f"startup_{analysis.id}"
            safe_name = "".join(ch if ch.isalnum() else "_" for ch in startup_name).strip("_").lower()
            safe_name = safe_name or "startup"
            output_path = os.path.join(pitch_dir, f"pitch_resultado_{safe_name}_{analysis.id}.pdf")
            export_pitch_pdf(
                pitch_payload,
                output_path,
                design_mode=design_mode,
                manual_template=design_template,
            )

            metadata = analysis.metadata or {}
            metadata["last_generated_pitch_payload"] = {
                "generated_at": timezone.now().isoformat(),
                "engine_used": pitch_payload.get("engine_used", model_source),
                "slide_count": len((pitch_payload.get("pitch_deck") or [])),
                "narrative_uniqueness_key": pitch_payload.get("narrative_uniqueness_key", ""),
                "design_mode": design_mode,
                "design_template": design_template,
            }
            analysis.metadata = metadata
            analysis.save(update_fields=["metadata", "updated_at"])

            return FileResponse(
                open(output_path, "rb"),
                as_attachment=True,
                filename=f"pitch_investidor_{safe_name}_{analysis.id}.pdf",
                content_type="application/pdf",
            )
        except Exception as exc:
            logger.error("Falha ao gerar pitch PDF a partir do resultado: %s", str(exc), exc_info=True)
            messages.error(request, f"Falha ao gerar pitch PDF: {_safe_exception_message(exc)}")
            return redirect("pitch_results", analysis_id=analysis.id)


class PitchExplainerVideoGenerateView(View):
    """Gera vídeo explicativo do potencial da startup com base na avaliação."""

    def post(self, request, analysis_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if analysis.user and request.user.is_authenticated and analysis.user_id != request.user.id:
            return redirect("dashboard")

        try:
            video_mode = (request.POST.get("video_mode", "auto") or "auto").strip().lower()
            allowed_modes = {"auto", "did_only", "local_only"}
            if video_mode not in allowed_modes:
                video_mode = "auto"

            existing_job_id = str((analysis.metadata or {}).get("explainer_video_job_id", "") or "").strip()
            if existing_job_id:
                existing_state = cache.get(_video_generation_cache_key(existing_job_id))
                if existing_state and existing_state.get("status") in {"PENDING", "RUNNING"}:
                    messages.info(request, "Já existe uma geração de vídeo em andamento para esta análise.")
                    return redirect(f"{reverse('pitch_results', kwargs={'analysis_id': analysis.id})}?video_job_id={existing_job_id}")

            presenter_image = request.FILES.get("presenter_image")
            if presenter_image:
                analysis.presenter_face_image_file = presenter_image
                analysis.save(update_fields=["presenter_face_image_file", "updated_at"])

            presenter_path = None
            presenter_url = None
            presenter_source_urls = []
            presenter_host = ""
            if analysis.presenter_face_image_file:
                try:
                    presenter_path = analysis.presenter_face_image_file.path
                except Exception:
                    presenter_path = None
                try:
                    presenter_url = request.build_absolute_uri(analysis.presenter_face_image_file.url)
                    # D-ID aceita apenas URLs HTTPS para source_url.
                    if presenter_url.startswith("http://"):
                        host = request.get_host().split(":")[0].lower()
                        presenter_host = host
                        if host not in {"localhost", "127.0.0.1", "testserver"}:
                            presenter_url = "https://" + presenter_url[len("http://") :]
                except Exception:
                    presenter_url = None

            if presenter_path and presenter_url:
                presenter_source_urls = build_did_presenter_source_urls(
                    presenter_image_path=presenter_path,
                    presenter_image_url=presenter_url,
                    startup_name=analysis.startup_name or "Startup",
                )

            if video_mode == "did_only" and not presenter_url:
                messages.error(
                    request,
                    "No modo D-ID, envie uma imagem real do apresentador antes de gerar o vídeo.",
                )
                return redirect("pitch_results", analysis_id=analysis.id)
            if video_mode == "did_only" and presenter_url and presenter_url.startswith("http://") and presenter_host in {"localhost", "127.0.0.1", "testserver"}:
                messages.error(
                    request,
                    "No modo D-ID, a imagem precisa de URL pública HTTPS. Abra o sistema pelo link externo e tente novamente.",
                )
                return redirect("pitch_results", analysis_id=analysis.id)

            metadata = analysis.metadata or {}
            job_id = _start_explainer_video_job(
                analysis=analysis,
                presenter_path=presenter_path,
                presenter_url=presenter_url,
                presenter_source_urls=presenter_source_urls,
                generation_mode=video_mode,
            )
            metadata["explainer_video_job_id"] = job_id
            metadata["explainer_video_job_status"] = "PENDING"
            metadata["explainer_video_source_images"] = len(presenter_source_urls or [])
            metadata["explainer_video_mode"] = video_mode
            analysis.metadata = metadata
            analysis.save(update_fields=["metadata", "updated_at"])
            messages.success(request, "Geração de vídeo iniciada. Acompanhe o progresso nesta página.")
            return redirect(f"{reverse('pitch_results', kwargs={'analysis_id': analysis.id})}?video_job_id={job_id}")
        except Exception as exc:
            logger.error("Falha ao gerar vídeo explicativo: %s", str(exc), exc_info=True)
            messages.error(
                request,
                "Não foi possível gerar o vídeo explicativo agora. Tente novamente em instantes.",
            )

        return redirect("pitch_results", analysis_id=analysis.id)


class PitchExplainerVideoProgressView(View):
    """Endpoint de progresso em tempo real para geração de vídeo explicativo."""

    def get(self, request, analysis_id, job_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if analysis.user and request.user.is_authenticated and analysis.user_id != request.user.id:
            return JsonResponse({"error": "Acesso negado"}, status=403)

        state = cache.get(_video_generation_cache_key(job_id))
        if not state:
            return JsonResponse({"error": "Job não encontrado"}, status=404)

        if int(state.get("analysis_id") or 0) != int(analysis.id):
            return JsonResponse({"error": "Job inválido para esta análise"}, status=403)

        return JsonResponse(state, status=200)


class ModelManagementView(LoginRequiredMixin, View):
    """Painel para gestão de modelos treinados"""

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

                models = _list_available_models()
                if len(models) <= 1:
                    raise ValueError("Não é possível excluir o único modelo disponível.")

                file_paths = [
                    get_model_path(model_name),
                    get_metrics_path(model_name),
                    get_meta_path(model_name),
                ]
                for file_path in file_paths:
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


class ModelTrainingProgressView(LoginRequiredMixin, View):
    """Endpoint de progresso em tempo real para jobs de treino de modelo."""

    def get(self, request, job_id):
        state = cache.get(_model_training_cache_key(job_id))
        if not state:
            return JsonResponse({"error": "Job não encontrado"}, status=404)
        return JsonResponse(state, status=200)


class InvestorDashboardView(View):
    """Dashboard público para investidores visualizarem potenciais de startups"""

    def get(self, request):
        try:
            min_score = float(request.GET.get("min_score", 0) or 0)
        except ValueError:
            min_score = 0.0
        try:
            max_score = float(request.GET.get("max_score", 10) or 10)
        except ValueError:
            max_score = 10.0
        try:
            days = int(request.GET.get("days", 180) or 180)
        except ValueError:
            days = 180
        engine = str(request.GET.get("engine", "all")).strip().lower()
        if engine not in {"all", "local", "gpt"}:
            engine = "all"

        min_score = max(0.0, min(10.0, min_score))
        max_score = max(0.0, min(10.0, max_score))
        if max_score < min_score:
            max_score = min_score

        analyses = PitchAnalysis.objects.exclude(success_score__isnull=True)
        if days > 0:
            analyses = analyses.filter(created_at__gte=timezone.now() - timedelta(days=days))
        if engine != "all":
            analyses = analyses.filter(metadata__analysis_engine_requested=engine)
        analyses = analyses.filter(success_score__gte=min_score, success_score__lte=max_score).order_by("-created_at")
        top_analyses = list(analyses[:12])

        for analysis in top_analyses:
            report = analysis.report or {}
            investor_pitch = report.get("investor_pitch", {}) if isinstance(report, dict) else {}
            if not investor_pitch:
                score = float(analysis.success_score or 0.0)
                thesis = "Oportunidade em monitoramento"
                if score >= 8:
                    thesis = "Tese de alto crescimento com potencial de escala acelerada"
                elif score >= 6:
                    thesis = "Tese com boa tração e espaço para ganho de eficiência"

                investor_pitch = {
                    "investment_thesis": thesis,
                    "funding_readiness": "Alta" if score >= 7.5 else ("Média" if score >= 5 else "Inicial"),
                    "capital_use_plan": [
                        "Expansão comercial orientada por dados",
                        "Fortalecimento de produto e retenção de clientes",
                        "Otimização de operações e margem",
                    ],
                }
            analysis.investor_pitch = investor_pitch

        total = analyses.count()
        summary = analyses.aggregate(
            avg_score=Avg("success_score"),
            max_score=Max("success_score"),
        )
        high_potential = analyses.filter(success_score__gte=7.5).count()

        recent_investor = list(analyses[:20])
        investor_labels = [f"#{a.id}" for a in recent_investor]
        investor_ids = [a.id for a in recent_investor]
        investor_scores = [float(a.success_score or 0) for a in recent_investor]
        investor_revenue = [float(a.revenue or 0) for a in recent_investor]
        investor_growth = [float(a.growth_rate or 0) for a in recent_investor]

        context = {
            "analyses": top_analyses,
            "kpi_total": total,
            "kpi_high_potential": high_potential,
            "kpi_avg_score": round(float(summary["avg_score"] or 0), 2),
            "kpi_max_score": round(float(summary["max_score"] or 0), 2),
            "active_model": get_active_model_name(),
            "investor_labels_json": json.dumps(investor_labels),
            "investor_ids_json": json.dumps(investor_ids),
            "investor_scores_json": json.dumps(investor_scores),
            "investor_revenue_json": json.dumps(investor_revenue),
            "investor_growth_json": json.dumps(investor_growth),
            "filter_min_score": min_score,
            "filter_max_score": max_score,
            "filter_days": days,
            "filter_engine": engine,
        }
        return render(request, "analyzer/investor_dashboard.html", context)





def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro realizado com sucesso!")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'analyzer/register.html', {'form': form})



