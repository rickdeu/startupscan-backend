from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_EMPREENDEDOR = "empreendedor"
    ROLE_INVESTIDOR = "investidor"
    ROLE_PUBLICO = "publico_geral"
    ROLE_ANALISTA = "analista"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_EMPREENDEDOR, "Empreendedor"),
        (ROLE_INVESTIDOR, "Investidor"),
        (ROLE_PUBLICO, "Público em geral"),
        (ROLE_ANALISTA, "Analista"),
        (ROLE_ADMIN, "Administrador"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Usuário",
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_PUBLICO,
        verbose_name="Perfil de acesso",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuário"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
