from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class IdeaPitchSubmission(models.Model):
    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("generated", "Pitch gerado"),
    ]

    MODEL_SOURCE_CHOICES = [
        ("local", "Local"),
        ("gpt", "GPT"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    startup_name = models.CharField(max_length=120, verbose_name="Nome da startup")
    one_liner = models.CharField(max_length=300, blank=True, default="")
    problem = models.TextField(verbose_name="Problema")
    solution = models.TextField(verbose_name="Solução")
    target_customer = models.TextField(verbose_name="Cliente-alvo")
    market_size = models.TextField(blank=True, default="")
    business_model = models.TextField(verbose_name="Modelo de negócio")
    competitive_advantage = models.TextField(blank=True, default="")
    traction = models.TextField(blank=True, default="")
    team = models.TextField(blank=True, default="")
    funding_goal = models.TextField(blank=True, default="")
    use_of_funds = models.TextField(blank=True, default="")
    call_to_action = models.TextField(blank=True, default="")

    model_source = models.CharField(
        max_length=10,
        choices=MODEL_SOURCE_CHOICES,
        default="local",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    generated_pitch = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Submissão de Ideia para Pitch"
        verbose_name_plural = "Submissões de Ideia para Pitch"

    def __str__(self):
        return f"{self.startup_name} ({self.get_status_display()})"


class IdeaPublicFeedback(models.Model):
    submission = models.ForeignKey(
        IdeaPitchSubmission,
        on_delete=models.CASCADE,
        related_name="public_feedbacks",
        verbose_name="Ideia",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="idea_public_feedbacks",
        verbose_name="Utilizador",
    )
    stars = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Estrelas (1 a 5)",
    )
    endorsed = models.BooleanField(default=False, verbose_name="Apoia esta ideia")
    comment = models.TextField(blank=True, default="", verbose_name="Comentário público")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Feedback Público de Ideia"
        verbose_name_plural = "Feedbacks Públicos de Ideias"
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "user"],
                name="unique_public_feedback_per_user_submission",
            )
        ]
        indexes = [
            models.Index(fields=["stars"]),
            models.Index(fields=["endorsed"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.submission.startup_name} ({self.stars} estrelas)"
