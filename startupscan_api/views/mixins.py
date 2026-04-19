from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from startupscan_api.roles import (
    ROLE_ADMIN,
    ROLE_ANALISTA,
    ROLE_EMPREENDEDOR,
    ROLE_INVESTIDOR,
    ROLE_PUBLICO,
    get_user_role,
)
from .helpers import _redirect_for_role


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = {ROLE_PUBLICO, ROLE_EMPREENDEDOR, ROLE_INVESTIDOR, ROLE_ANALISTA, ROLE_ADMIN}

    def dispatch(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role == ROLE_ADMIN:
            return super().dispatch(request, *args, **kwargs)
        if role not in set(self.allowed_roles or []):
            messages.error(request, "O seu perfil não tem permissão para acessar esta página.")
            return _redirect_for_role(request, fallback_role=role)
        return super().dispatch(request, *args, **kwargs)
