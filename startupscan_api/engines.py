from django.db import models


class AnalysisEngine(models.TextChoices):
    """Single source of truth for the idea/pitch analysis engines.

    Kept dependency-free (only django.db.models) so both startupscan_api and
    subscriptions can import it without risking a circular import.
    """

    LOCAL = "local", "Local"
    GPT = "gpt", "GPT"
    DEEPSEEK = "deepseek", "DeepSeek"
    OLLAMA = "ollama", "Ollama"


def normalize_engine(value, default: str = AnalysisEngine.LOCAL) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in AnalysisEngine.values else default
