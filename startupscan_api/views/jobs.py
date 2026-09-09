import os
import logging
import threading
import uuid
from pathlib import Path

import joblib
import pandas as pd

from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.management import call_command
from django.db import close_old_connections
from django.utils import timezone

from startupscan_api.models import PitchAnalysis
from startupscan_api.modeling import train_and_evaluate
from startupscan_api.services.model_registry import (
    get_metrics_path,
    get_model_path,
    set_active_model,
)
from .helpers import (
    _normalize_model_name,
    _write_json_file,
    _generate_explainer_video_lazy,
)

logger = logging.getLogger(__name__)

MODEL_TRAINING_CACHE_PREFIX = "model_training_job"
MODEL_TRAINING_TTL_SECONDS = 60 * 60 * 24
VIDEO_GENERATION_CACHE_PREFIX = "explainer_video_job"
VIDEO_GENERATION_TTL_SECONDS = 60 * 60 * 24

# Video generation runs in a background thread with no request context, so
# its phase/message strings can't read startupscan_api.i18n's ui_language
# from the request. Only English and Portuguese are implemented; any other
# selected language falls back to English (never Portuguese), matching the
# same product decision applied to the pitch-deck generator.
_VIDEO_JOB_STRINGS = {
    "en": {
        "phase_fila": "queued",
        "phase_inicializacao": "initializing",
        "phase_preparacao": "preparing",
        "phase_renderizacao": "rendering",
        "phase_persistencia": "saving",
        "phase_concluido": "completed",
        "phase_falha": "failed",
        "msg_default_queued": "Waiting for video generation to start",
        "msg_job_created": "Video job created, waiting to run",
        "msg_initializing": "Initializing explainer video generation",
        "msg_preparing": "Preparing visual and audio resources",
        "msg_rendering_start": "Creating executive script and starting rendering",
        "msg_processing_default": "Processing video...",
        "msg_persisting": "Saving video to the analysis result",
        "msg_completed": "Explainer video generated successfully",
        "msg_failed": "Failed to generate video: {detail}",
    },
    "pt": {
        "phase_fila": "fila",
        "phase_inicializacao": "inicialização",
        "phase_preparacao": "preparação",
        "phase_renderizacao": "renderização",
        "phase_persistencia": "persistência",
        "phase_concluido": "concluído",
        "phase_falha": "falha",
        "msg_default_queued": "Aguardando início da geração de vídeo",
        "msg_job_created": "Job de vídeo criado, aguardando execução",
        "msg_initializing": "Inicializando geração do vídeo explicativo",
        "msg_preparing": "Preparando recursos visuais e áudio",
        "msg_rendering_start": "Criando roteiro executivo e iniciando renderização",
        "msg_processing_default": "Processando vídeo...",
        "msg_persisting": "Salvando vídeo no resultado da análise",
        "msg_completed": "Vídeo explicativo gerado com sucesso",
        "msg_failed": "Falha ao gerar vídeo: {detail}",
    },
}


def _video_job_text(language: str, key: str, **kwargs) -> str:
    strings = _VIDEO_JOB_STRINGS.get(language) or _VIDEO_JOB_STRINGS["en"]
    template = strings.get(key) or _VIDEO_JOB_STRINGS["en"].get(key, key)
    return template.format(**kwargs) if kwargs else template


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


def _write_video_generation_state(job_id: str, *, language: str = "en", **updates):
    key = _video_generation_cache_key(job_id)
    state = cache.get(key) or {
        "job_id": job_id,
        "status": "PENDING",
        "progress": 0,
        "phase": _video_job_text(language, "phase_fila"),
        "message": _video_job_text(language, "msg_default_queued"),
    }
    state.update(updates)
    state["updated_at"] = timezone.now().isoformat()
    cache.set(key, state, VIDEO_GENERATION_TTL_SECONDS)
    return state


def _run_explainer_video_job(
    job_id: str,
    analysis_id: int,
    presenter_path=None,
    presenter_url=None,
    presenter_source_urls=None,
    presenter_gender_choice: str = "auto",
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
        canva_context_meta = {}
        if generation_mode == "canva_capcut":
            try:
                from startupscan_api.services.pitch_video import _canva_capcut_context_for_meta
                canva_context_meta = _canva_capcut_context_for_meta(analysis)
            except Exception:
                canva_context_meta = {}

        media_root = settings.MEDIA_ROOT
        try:
            os.makedirs(media_root, exist_ok=True)
        except OSError:
            media_root = os.path.join(settings.BASE_DIR, "media")
            os.makedirs(media_root, exist_ok=True)

        temp_dir = os.path.join(media_root, "generated_videos")
        os.makedirs(temp_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_output = os.path.join(temp_dir, f"explainer_{analysis.id}_{timestamp}.mp4")

        _write_video_generation_state(job_id, status="RUNNING", progress=24, phase="preparacao",
                                      message="Preparando recursos visuais e áudio")
        _write_video_generation_state(job_id, status="RUNNING", progress=35, phase="renderizacao",
                                      message="Criando roteiro executivo e iniciando renderização")

        def _video_progress_callback(progress_pct: int, phase: str, message: str):
            bounded = max(35, min(94, int(progress_pct)))
            _write_video_generation_state(
                job_id,
                status="RUNNING",
                progress=bounded,
                phase=phase or "renderizacao",
                message=message or "Processando vídeo...",
            )

        video_meta = _generate_explainer_video_lazy(
            analysis,
            temp_output,
            presenter_image_path=presenter_path,
            presenter_image_url=presenter_url,
            presenter_source_urls=presenter_source_urls or [],
            presenter_gender_override=presenter_gender_choice,
            generation_mode=generation_mode,
            progress_callback=_video_progress_callback,
        )

        _write_video_generation_state(job_id, status="RUNNING", progress=78, phase="persistencia",
                                      message="Salvando vídeo no resultado da análise")

        final_name = f"explainer_{analysis.id}.mp4"
        with open(temp_output, "rb") as fh:
            analysis.explainer_video_file.save(final_name, File(fh), save=False)

        metadata = analysis.metadata or {}
        metadata["explainer_video"] = video_meta
        if generation_mode == "canva_capcut" and canva_context_meta:
            if isinstance(metadata.get("explainer_video"), dict):
                metadata["explainer_video"].update(canva_context_meta)
        metadata["explainer_video_job_id"] = job_id
        metadata["explainer_video_job_status"] = "COMPLETED"
        metadata["explainer_video_mode"] = generation_mode
        metadata["explainer_video_gender_choice"] = presenter_gender_choice
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
            metadata["explainer_video_gender_choice"] = presenter_gender_choice
            metadata["explainer_video_job_error"] = error_detail
            explainer_video_meta = metadata.get("explainer_video")
            if not isinstance(explainer_video_meta, dict):
                explainer_video_meta = {}
            explainer_video_meta.update({
                "status": "failed",
                "error": error_detail,
                "generated_at": timezone.now().isoformat(),
            })
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
            logger.exception("Erro ao salvar metadados de vídeo para análise %s", analysis_id)
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
            presenter_gender_choice=presenter_gender_choice,
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
    presenter_path=None,
    presenter_url=None,
    presenter_source_urls=None,
    presenter_gender_choice: str = "auto",
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
        presenter_gender_choice=presenter_gender_choice,
    )
    thread = threading.Thread(
        target=_run_explainer_video_job,
        kwargs={
            "job_id": job_id,
            "analysis_id": analysis.id,
            "presenter_path": presenter_path,
            "presenter_url": presenter_url,
            "presenter_source_urls": presenter_source_urls or [],
            "presenter_gender_choice": presenter_gender_choice,
            "generation_mode": generation_mode,
        },
        daemon=True,
    )
    thread.start()
    return job_id


def _run_model_training_job(
    job_id: str,
    action: str,
    model_name: str = "",
    dataset_source: str = "default",
):
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


def _start_model_training_job(
    action: str,
    model_name: str = "",
    dataset_source: str = "default",
) -> str:
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
