from __future__ import annotations

from django.conf import settings
from django.utils import translation

from startupscan_api.i18n import normalize_ui_language, to_django_language


class UiLanguageMiddleware:
    """
    Middleware para persistir idioma da UI (inclui Umbundu) e sincronizar
    o locale Django com fallback quando necessario.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        requested = (
            request.GET.get("lang")
            or request.POST.get("language")
            or request.session.get("ui_language")
            or request.COOKIES.get("ui_language")
            or settings.LANGUAGE_CODE
        )
        ui_lang = normalize_ui_language(requested)
        django_lang = to_django_language(ui_lang)

        request.ui_language = ui_lang
        request.LANGUAGE_CODE = django_lang
        translation.activate(django_lang)

        response = self.get_response(request)
        request.session["ui_language"] = ui_lang
        response.set_cookie("ui_language", ui_lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            django_lang,
            max_age=60 * 60 * 24 * 365,
            samesite="Lax",
        )
        return response
