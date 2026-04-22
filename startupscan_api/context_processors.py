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

    user_subscription = None
    user_plan_tier = None
    subscription_trial_days_left = 0
    if user and getattr(user, "is_authenticated", False):
        try:
            user_subscription = user.subscription
            user_plan_tier = user_subscription.plan_tier
            subscription_trial_days_left = user_subscription.trial_days_left
        except Exception:
            pass

    return {
        "user_role": role,
        "user_role_label": role_label(role),
        "user_role_home_url_name": role_home_url_name(role),
        "user_role_access": access,
        "role_publico": ROLE_PUBLICO,
        "current_ui_language": current_ui_language,
        "ui_languages": SUPPORTED_UI_LANGUAGES,
        "ui_text": build_ui_text(current_ui_language),
        "user_subscription": user_subscription,
        "user_plan_tier": user_plan_tier,
        "subscription_trial_days_left": subscription_trial_days_left,
    }

