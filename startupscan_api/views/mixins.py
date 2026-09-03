from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from startupscan_api.i18n import build_ui_text, normalize_ui_language
from startupscan_api.roles import (
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_ENTREPRENEUR,
    ROLE_INVESTOR,
    ROLE_GENERAL_PUBLIC,
    get_user_role,
)
from .helpers import _redirect_for_role


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = {ROLE_GENERAL_PUBLIC, ROLE_ENTREPRENEUR, ROLE_INVESTOR, ROLE_ANALYST, ROLE_ADMIN}

    def dispatch(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role == ROLE_ADMIN:
            return super().dispatch(request, *args, **kwargs)
        if role not in set(self.allowed_roles or []):
            ui_text = build_ui_text(normalize_ui_language(getattr(request, "ui_language", None)))
            messages.error(request, ui_text.get(
                "msg_role_not_permitted", "Your profile does not have permission to access this page.",
            ))
            return _redirect_for_role(request, fallback_role=role)
        return super().dispatch(request, *args, **kwargs)
