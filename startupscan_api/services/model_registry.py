import json
import os
from pathlib import Path

from django.conf import settings


DEFAULT_MODEL_NAME = "pitch_model.pkl"


def get_registry_path():
    return Path(settings.AI_MODELS_DIR) / "model_registry.json"


def get_model_path(model_name):
    return Path(settings.AI_MODELS_DIR) / model_name


def get_metrics_path(model_name):
    return Path(settings.AI_MODELS_DIR) / f"{Path(model_name).stem}_metrics.json"


def get_meta_path(model_name):
    return Path(settings.AI_MODELS_DIR) / f"{Path(model_name).stem}_meta.json"


def load_registry():
    path = get_registry_path()
    if not path.exists():
        return {"active_model": DEFAULT_MODEL_NAME}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if not isinstance(data, dict):
                return {"active_model": DEFAULT_MODEL_NAME}
            data.setdefault("active_model", DEFAULT_MODEL_NAME)
            return data
    except Exception:
        return {"active_model": DEFAULT_MODEL_NAME}


def save_registry(registry):
    os.makedirs(settings.AI_MODELS_DIR, exist_ok=True)
    path = get_registry_path()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, ensure_ascii=False, indent=2)


def get_active_model_name():
    registry = load_registry()
    return registry.get("active_model", DEFAULT_MODEL_NAME)


def set_active_model(model_name):
    registry = load_registry()
    registry["active_model"] = model_name
    save_registry(registry)


def read_json(path):
    if not Path(path).exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
