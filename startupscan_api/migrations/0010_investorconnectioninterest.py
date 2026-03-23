from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("startupscan_api", "0009_userprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="InvestorConnectionInterest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("reviewing", "Em análise"),
                            ("connected", "Conexão iniciada"),
                            ("rejected", "Recusado"),
                            ("withdrawn", "Retirado"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Status da conexão",
                    ),
                ),
                ("investor_message", models.TextField(blank=True, default="", verbose_name="Mensagem do investidor")),
                ("entrepreneur_reply", models.TextField(blank=True, default="", verbose_name="Resposta do empreendedor")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connection_interests",
                        to="startupscan_api.pitchanalysis",
                        verbose_name="Análise de interesse",
                    ),
                ),
                (
                    "entrepreneur",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="received_connection_interests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Empreendedor",
                    ),
                ),
                (
                    "investor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_connection_interests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Investidor",
                    ),
                ),
            ],
            options={
                "verbose_name": "Interesse de Conexão",
                "verbose_name_plural": "Interesses de Conexão",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="investorconnectioninterest",
            constraint=models.UniqueConstraint(
                fields=("analysis", "investor"),
                name="unique_interest_per_investor_analysis",
            ),
        ),
        migrations.AddIndex(
            model_name="investorconnectioninterest",
            index=models.Index(fields=["status"], name="startupscan_status_67753f_idx"),
        ),
        migrations.AddIndex(
            model_name="investorconnectioninterest",
            index=models.Index(fields=["created_at"], name="startupscan_created_56184f_idx"),
        ),
        migrations.AddIndex(
            model_name="investorconnectioninterest",
            index=models.Index(fields=["updated_at"], name="startupscan_updated_7c416b_idx"),
        ),
    ]

