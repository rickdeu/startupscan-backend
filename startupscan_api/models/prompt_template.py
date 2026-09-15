from django.conf import settings
from django.db import models

from startupscan_api.services.ai_engines.prompt_defaults import (
    DEFAULT_PROMPTS,
    PROMPT_ENGINE_CHOICES,
    PURPOSE_CHOICES,
)


class PromptTemplate(models.Model):
    """
    Editable LLM prompt text per (engine, purpose), so prompts can be tuned
    from the super-admin panel without a code deploy. Seeded from the
    built-in defaults (see prompt_defaults.py) by a data migration; falls
    back to those same defaults at runtime if a row is missing or inactive.

    Content uses Python `string.Template` placeholders ($name / ${name})
    rather than str.format() specifically so admins can paste literal JSON
    examples into the prompt without ever needing to escape curly braces.
    """

    engine = models.CharField(max_length=20, choices=PROMPT_ENGINE_CHOICES, verbose_name="Engine")
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, verbose_name="Purpose")
    content = models.TextField(
        verbose_name="Prompt content",
        help_text="Uses $variable placeholders. Literal { and } (e.g. JSON examples) never need escaping.",
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Active",
        help_text="When off, this engine falls back to the built-in default prompt for this slot.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Last updated by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["engine", "purpose"]
        verbose_name = "Prompt Template"
        verbose_name_plural = "Prompt Templates"
        constraints = [
            models.UniqueConstraint(fields=["engine", "purpose"], name="unique_prompt_per_engine_purpose"),
        ]

    def __str__(self):
        return f"{self.get_engine_display()} — {self.get_purpose_display()}"

    @property
    def default_content(self) -> str:
        return DEFAULT_PROMPTS.get(self.purpose, "")
