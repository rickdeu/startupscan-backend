import os
import json
import logging
from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.shortcuts import redirect

from startupscan_api.services.model_registry import (
    get_active_model_name,
    get_meta_path,
    get_metrics_path,
    get_model_path,
)
from startupscan_api.roles import get_user_role, role_home_url_name
from startupscan_api.services.pitch_builder import (
    PITCH_DESIGN_MODE_AUTO,
    normalize_pitch_design_options,
)

logger = logging.getLogger(__name__)


def _build_did_presenter_sources_lazy(*args, **kwargs):
    from startupscan_api.services.pitch_video import build_did_presenter_source_urls
    return build_did_presenter_source_urls(*args, **kwargs)


def _detect_presenter_gender_lazy(*args, **kwargs):
    from startupscan_api.services.pitch_video import detect_presenter_gender
    return detect_presenter_gender(*args, **kwargs)


def _generate_explainer_video_lazy(*args, **kwargs):
    from startupscan_api.services.pitch_video import generate_explainer_video
    return generate_explainer_video(*args, **kwargs)


def _safe_exception_message(exc: Exception, max_len: int = 280) -> str:
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


def _inject_i18n_labels(context: dict, request) -> dict:
    context = dict(context or {})
    ui_text = context.get("ui_text")
    if not isinstance(ui_text, dict):
        try:
            from startupscan_api.i18n import build_ui_text
            ui_text = build_ui_text(getattr(request, "ui_language", None))
        except Exception:
            ui_text = {}
        context["ui_text"] = ui_text

    context["ui_days_labels"] = {
        "30": ui_text.get("days_last_30", "Últimos 30 dias"),
        "90": ui_text.get("days_last_90", "Últimos 90 dias"),
        "180": ui_text.get("days_last_180", "Últimos 180 dias"),
        "365": ui_text.get("days_last_12m", "Últimos 12 meses"),
        "0": ui_text.get("days_all_period", "Todo o período"),
    }
    context["ui_phase_labels"] = {
        "queue": ui_text.get("phase_queue", "Fila"),
        "initialization": ui_text.get("phase_initialization", "Inicialização"),
        "preparation": ui_text.get("phase_preparation", "Preparação"),
        "rendering": ui_text.get("phase_rendering", "Renderização"),
        "persistence": ui_text.get("phase_persistence", "Persistência"),
        "completed": ui_text.get("phase_completed", "Concluído"),
        "failed": ui_text.get("phase_failed", "Falha"),
        "processing": ui_text.get("phase_processing", "Processando"),
    }
    context["ui_status_labels"] = {
        "running": ui_text.get("status_running", "RUNNING"),
        "pending": ui_text.get("status_pending", "PENDING"),
        "completed": ui_text.get("status_completed", "COMPLETED"),
        "failed": ui_text.get("status_failed", "FAILED"),
        "unavailable": ui_text.get("status_unavailable", "UNAVAILABLE"),
    }
    return context


def _redirect_for_role(request, *, fallback_role=None):
    target_role = fallback_role or get_user_role(request.user)
    return redirect(role_home_url_name(target_role))


def _redirect_back_or_default(request, default_name: str):
    referer = (request.META.get("HTTP_REFERER") or "").strip()
    if referer:
        return redirect(referer)
    return redirect(default_name)


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


def _normalize_model_name(raw_model_name: str, action: str) -> str:
    raw_model_name = (raw_model_name or "").strip()
    if action == "train_new":
        return _safe_slug_model_name(raw_model_name)
    if raw_model_name.endswith(".pkl"):
        return raw_model_name
    return _safe_slug_model_name(raw_model_name)


def _resolve_pitch_design_selection(request, *, default_mode=None, default_template=None):
    mode = (request.GET.get("design_mode", "") or "").strip().lower() or (default_mode or PITCH_DESIGN_MODE_AUTO)
    template = (request.GET.get("design_template", "") or "").strip().lower() or (default_template or "")
    return normalize_pitch_design_options(mode, template)


def _read_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.warning("Falha ao ler ficheiro JSON: %s", path)
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
        models.append({
            "name": model_name,
            "display_name": meta.get(
                "display_name",
                model_name.replace(".pkl", "").replace("-", " ").title(),
            ),
            "description": meta.get("description", ""),
            "is_active": model_name == active_model,
            "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
            "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime),
            "metrics": metrics,
            "consistency_accuracy_pct": consistency if consistency is not None else None,
            "cv_r2_pct": round(float(cv_r2) * 100, 2) if cv_r2 is not None else None,
        })
    return models
