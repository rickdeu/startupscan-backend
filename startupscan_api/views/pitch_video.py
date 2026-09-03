import logging
import os
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from startupscan_api.i18n import build_ui_text, normalize_ui_language
from startupscan_api.models import PitchAnalysis
from startupscan_api.roles import ROLE_ADMIN, ROLE_ANALYST, ROLE_ENTREPRENEUR, get_user_role
from .helpers import (
    _build_did_presenter_sources_lazy,
    _detect_presenter_gender_lazy,
    _safe_exception_message,
)
from .jobs import _start_explainer_video_job, _video_generation_cache_key
from .mixins import RoleRequiredMixin
from subscriptions.mixins import SubscriptionGate

logger = logging.getLogger(__name__)


def _ui_text_for_request(request):
    language = normalize_ui_language(getattr(request, "ui_language", None))
    return build_ui_text(language)


class PitchExplainerVideoGenerateView(SubscriptionGate, RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_ANALYST, ROLE_ADMIN}
    required_feature = 'video_generation'
    required_counter = 'videos_per_month'
    usage_field = 'videos_count'

    def post(self, request, analysis_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if (
            get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST)
            and analysis.user
            and request.user.is_authenticated
            and analysis.user_id != request.user.id
        ):
            return redirect("dashboard")

        try:
            video_mode = (request.POST.get("video_mode", "auto") or "auto").strip().lower()
            allowed_modes = {"auto", "did_only", "local_only", "canva_capcut"}
            if video_mode not in allowed_modes:
                video_mode = "auto"

            presenter_gender_choice = (request.POST.get("presenter_gender_choice", "auto") or "auto").strip().lower()
            if presenter_gender_choice not in {"auto", "male", "female"}:
                presenter_gender_choice = "auto"

            existing_job_id = str((analysis.metadata or {}).get("explainer_video_job_id", "") or "").strip()
            if existing_job_id:
                existing_state = cache.get(_video_generation_cache_key(existing_job_id))
                if existing_state and existing_state.get("status") in {"PENDING", "RUNNING"}:
                    from django.contrib import messages
                    messages.info(request, _ui_text_for_request(request).get(
                        "msg_video_already_generating",
                        "A video generation is already in progress for this analysis.",
                    ))
                    return redirect(
                        f"{reverse('pitch_results', kwargs={'analysis_id': analysis.id})}?video_job_id={existing_job_id}"
                    )

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
                    if presenter_url.startswith("http://"):
                        host = request.get_host().split(":")[0].lower()
                        presenter_host = host
                        if host not in {"localhost", "127.0.0.1", "testserver"}:
                            presenter_url = "https://" + presenter_url[len("http://"):]
                except Exception:
                    presenter_url = None

            if presenter_path and presenter_url:
                if video_mode == "did_only":
                    presenter_source_urls = [presenter_url]
                else:
                    presenter_source_urls = _build_did_presenter_sources_lazy(
                        presenter_image_path=presenter_path,
                        presenter_image_url=presenter_url,
                        startup_name=analysis.startup_name or "Startup",
                    )
                    if presenter_url not in presenter_source_urls:
                        presenter_source_urls.insert(0, presenter_url)

            if video_mode == "did_only" and not presenter_url:
                from django.contrib import messages
                messages.error(request, _ui_text_for_request(request).get(
                    "msg_did_mode_requires_presenter_image",
                    "In D-ID mode, upload a real presenter photo before generating the video.",
                ))
                return redirect("pitch_results", analysis_id=analysis.id)

            if (
                video_mode == "did_only"
                and presenter_url
                and presenter_url.startswith("http://")
                and presenter_host in {"localhost", "127.0.0.1", "testserver"}
            ):
                from django.contrib import messages
                messages.error(
                    request,
                    _ui_text_for_request(request).get(
                        "msg_did_requires_public_https_image",
                        "In D-ID mode, the image needs a public HTTPS URL. Open the system via the external link and try again.",
                    ),
                )
                return redirect("pitch_results", analysis_id=analysis.id)

            job_id = _start_explainer_video_job(
                analysis=analysis,
                presenter_path=presenter_path,
                presenter_url=presenter_url,
                presenter_source_urls=presenter_source_urls,
                presenter_gender_choice=presenter_gender_choice,
                generation_mode=video_mode,
            )

            if request.user.is_authenticated and get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST):
                from subscriptions.models import MonthlyUsage
                MonthlyUsage.increment(request.user, 'videos_count')

            metadata = analysis.metadata or {}
            metadata["explainer_video_job_id"] = job_id
            metadata["explainer_video_job_status"] = "PENDING"
            metadata["explainer_video_source_images"] = len(presenter_source_urls or [])
            metadata["explainer_video_real_image_only"] = bool(video_mode == "did_only")
            metadata["explainer_video_mode"] = video_mode
            metadata["explainer_video_gender_choice"] = presenter_gender_choice
            analysis.metadata = metadata
            analysis.save(update_fields=["metadata", "updated_at"])

            from django.contrib import messages
            messages.success(request, _ui_text_for_request(request).get(
                "msg_video_generation_started",
                "Video generation started. Track the progress on this page.",
            ))
            return redirect(
                f"{reverse('pitch_results', kwargs={'analysis_id': analysis.id})}?video_job_id={job_id}"
            )

        except Exception as exc:
            logger.error("Falha ao gerar vídeo explicativo: %s", str(exc), exc_info=True)
            from django.contrib import messages
            messages.error(request, _ui_text_for_request(request).get(
                "msg_video_generation_failed",
                "Could not generate the explainer video right now. Please try again shortly.",
            ))

        return redirect("pitch_results", analysis_id=analysis.id)


class PitchPresenterGenderDetectView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_ANALYST, ROLE_ADMIN}

    def post(self, request, analysis_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if (
            get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST)
            and analysis.user
            and request.user.is_authenticated
            and analysis.user_id != request.user.id
        ):
            return JsonResponse({"ok": False, "error": "Acesso negado."}, status=403)

        presenter_image = request.FILES.get("presenter_image")
        if not presenter_image:
            return JsonResponse({"ok": False, "error": "Envie uma imagem para detectar o gênero."}, status=400)

        suffix = Path(getattr(presenter_image, "name", "") or "").suffix or ".jpg"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                for chunk in presenter_image.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name

            detected = _detect_presenter_gender_lazy(tmp_path)
            gender = str(detected.get("gender", "unknown") or "unknown").lower()
            if gender not in {"male", "female", "unknown"}:
                gender = "unknown"

            labels = {"male": "Homem", "female": "Mulher", "unknown": "Não identificado"}
            confidence = detected.get("confidence")
            confidence_pct = round(float(confidence) * 100.0, 1) if confidence is not None else None

            return JsonResponse({
                "ok": True,
                "detected_gender": gender,
                "detected_gender_label": labels[gender],
                "confidence": confidence,
                "confidence_pct": confidence_pct,
                "method": detected.get("method", "unknown"),
            }, status=200)

        except Exception as exc:
            logger.error("Falha ao detectar gênero do apresentador: %s", str(exc), exc_info=True)
            return JsonResponse({"ok": False, "error": _safe_exception_message(exc)}, status=500)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


class PitchExplainerVideoProgressView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_ANALYST, ROLE_ADMIN}

    def get(self, request, analysis_id, job_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if (
            get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST)
            and analysis.user
            and request.user.is_authenticated
            and analysis.user_id != request.user.id
        ):
            return JsonResponse({"error": "Acesso negado"}, status=403)

        state = cache.get(_video_generation_cache_key(job_id))
        if not state:
            return JsonResponse({"error": "Job não encontrado"}, status=404)
        if int(state.get("analysis_id") or 0) != int(analysis.id):
            return JsonResponse({"error": "Job inválido para esta análise"}, status=403)

        return JsonResponse(state, status=200)
