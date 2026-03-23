from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _backfill_user_profiles(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("startupscan_api", "UserProfile")
    for user in User.objects.all().only("id"):
        UserProfile.objects.get_or_create(user_id=user.id, defaults={"role": "publico_geral"})


class Migration(migrations.Migration):
    dependencies = [
        ("startupscan_api", "0008_add_presenter_face_to_pitchanalysis"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("empreendedor", "Empreendedor"),
                            ("investidor", "Investidor"),
                            ("publico_geral", "Público em geral"),
                            ("analista", "Analista"),
                            ("admin", "Administrador"),
                        ],
                        default="publico_geral",
                        max_length=30,
                        verbose_name="Perfil de acesso",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuário",
                    ),
                ),
            ],
            options={
                "verbose_name": "Perfil de Usuário",
                "verbose_name_plural": "Perfis de Usuário",
            },
        ),
        migrations.RunPython(_backfill_user_profiles, migrations.RunPython.noop),
    ]

