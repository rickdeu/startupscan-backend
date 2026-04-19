from django.db import models
from django.contrib.auth.models import User
from .pitch import PitchAnalysis


class InvestorConnectionInterest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_REVIEWING = "reviewing"
    STATUS_CONNECTED = "connected"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendente"),
        (STATUS_REVIEWING, "Em análise"),
        (STATUS_CONNECTED, "Conexão iniciada"),
        (STATUS_REJECTED, "Recusado"),
        (STATUS_WITHDRAWN, "Retirado"),
    ]

    analysis = models.ForeignKey(
        PitchAnalysis,
        on_delete=models.CASCADE,
        related_name="connection_interests",
        verbose_name="Análise de interesse",
    )
    investor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_connection_interests",
        verbose_name="Investidor",
    )
    entrepreneur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_connection_interests",
        verbose_name="Empreendedor",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Status da conexão",
    )
    investor_message = models.TextField(
        blank=True, default="", verbose_name="Mensagem do investidor"
    )
    entrepreneur_reply = models.TextField(
        blank=True, default="", verbose_name="Resposta do empreendedor"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Interesse de Conexão"
        verbose_name_plural = "Interesses de Conexão"
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "investor"],
                name="unique_interest_per_investor_analysis",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        startup = self.analysis.startup_name or f"Análise #{self.analysis_id}"
        return f"{self.investor.username} -> {startup} ({self.status})"
