from django.contrib.auth.models import User
from django.db import models


class ActivityLog(models.Model):
    """Audit trail of relevant operations performed across the platform.

    Populated by :func:`superadmin.activity.log_activity`, called from the
    regular app views (report generated/viewed/downloaded, analysis created,
    video generated, etc.) so the super admin can see real usage volume.
    """

    ACTION_ANALYSIS_CREATED = "analysis_created"
    ACTION_BATCH_ANALYSIS = "batch_analysis"
    ACTION_REPORT_VIEWED = "report_viewed"
    ACTION_REPORT_DOWNLOADED = "report_downloaded"
    ACTION_PITCH_PDF_GENERATED = "pitch_pdf_generated"
    ACTION_VIDEO_GENERATED = "video_generated"
    ACTION_IDEA_CREATED = "idea_created"
    ACTION_IDEA_PDF_GENERATED = "idea_pdf_generated"
    ACTION_INVESTOR_INTEREST_SENT = "investor_interest_sent"

    ACTION_CHOICES = [
        (ACTION_ANALYSIS_CREATED, "Analysis created"),
        (ACTION_BATCH_ANALYSIS, "Batch analysis run"),
        (ACTION_REPORT_VIEWED, "Report viewed"),
        (ACTION_REPORT_DOWNLOADED, "Report downloaded (PDF)"),
        (ACTION_PITCH_PDF_GENERATED, "Investor pitch PDF generated"),
        (ACTION_VIDEO_GENERATED, "Explainer video generated"),
        (ACTION_IDEA_CREATED, "Idea pitch created"),
        (ACTION_IDEA_PDF_GENERATED, "Idea pitch PDF generated"),
        (ACTION_INVESTOR_INTEREST_SENT, "Investor interest sent"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name="User",
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES, db_index=True, verbose_name="Action")
    target_repr = models.CharField(max_length=255, blank=True, default="", verbose_name="Target")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP address")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="When")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        who = self.user.username if self.user else "anonymous"
        return f"{self.get_action_display()} — {who} @ {self.created_at:%Y-%m-%d %H:%M}"
