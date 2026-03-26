from startupscan_api.roles import (
    ROLE_PUBLICO,
    get_user_role,
    role_access_matrix,
    role_home_url_name,
    role_label,
)
from startupscan_api.i18n import SUPPORTED_UI_LANGUAGES, build_ui_text, normalize_ui_language
from startupscan_api.modules.subscriptions.access import get_subscription_and_access_for_user


def user_role_context(request):
    user = getattr(request, "user", None)
    role = get_user_role(user)
    access = role_access_matrix(role)
    subscription, subscription_access = get_subscription_and_access_for_user(user)
    current_ui_language = normalize_ui_language(
        getattr(request, "ui_language", None) or request.session.get("ui_language")
    )
    effective_access = dict(access)
    for key, allowed in (subscription_access or {}).items():
        if key in effective_access:
            effective_access[key] = bool(effective_access.get(key) and allowed)
        else:
            effective_access[key] = bool(allowed)
    return {
        "user_role": role,
        "user_role_label": role_label(role),
        "user_role_home_url_name": role_home_url_name(role),
        "user_role_access": effective_access,
        "user_role_access_role_only": access,
        "user_subscription_access": subscription_access,
        "user_subscription": subscription,
        "role_publico": ROLE_PUBLICO,
        "current_ui_language": current_ui_language,
        "ui_languages": SUPPORTED_UI_LANGUAGES,
        "ui_text": build_ui_text(current_ui_language),
    }

