from startupscan_api.roles import (
    ROLE_PUBLICO,
    get_user_role,
    role_access_matrix,
    role_home_url_name,
    role_label,
)
from startupscan_api.i18n import SUPPORTED_UI_LANGUAGES, build_ui_text, normalize_ui_language


def user_role_context(request):
    user = getattr(request, "user", None)
    role = get_user_role(user)
    access = role_access_matrix(role)
    current_ui_language = normalize_ui_language(
        getattr(request, "ui_language", None) or request.session.get("ui_language")
    )
    return {
        "user_role": role,
        "user_role_label": role_label(role),
        "user_role_home_url_name": role_home_url_name(role),
        "user_role_access": access,
        "role_publico": ROLE_PUBLICO,
        "current_ui_language": current_ui_language,
        "ui_languages": SUPPORTED_UI_LANGUAGES,
        "ui_text": build_ui_text(current_ui_language),
    }

