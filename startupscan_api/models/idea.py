from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class IdeaPitchSubmission(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("generated", "Pitch generated"),
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
        verbose_name="User",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    startup_name = models.CharField(max_length=120, verbose_name="Startup name")
    one_liner = models.CharField(max_length=300, blank=True, default="")
    problem = models.TextField(verbose_name="Problem")
    solution = models.TextField(verbose_name="Solution")
    target_customer = models.TextField(verbose_name="Target customer")
    market_size = models.TextField(blank=True, default="")
    business_model = models.TextField(verbose_name="Business model")
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
        verbose_name = "Idea Pitch Submission"
        verbose_name_plural = "Idea Pitch Submissions"

    def __str__(self):
        return f"{self.startup_name} ({self.get_status_display()})"


class IdeaPublicFeedback(models.Model):
    submission = models.ForeignKey(
        IdeaPitchSubmission,
        on_delete=models.CASCADE,
        related_name="public_feedbacks",
        verbose_name="Idea",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="idea_public_feedbacks",
        verbose_name="User",
    )
    stars = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Stars (1 to 5)",
    )
    endorsed = models.BooleanField(default=False, verbose_name="Endorses this idea")
    comment = models.TextField(blank=True, default="", verbose_name="Public comment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Idea Public Feedback"
        verbose_name_plural = "Idea Public Feedbacks"
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
        return f"{self.user.username} -> {self.submission.startup_name} ({self.stars} stars)"
