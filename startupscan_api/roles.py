from django.urls import reverse
from django.db import OperationalError, ProgrammingError

from startupscan_api.models import UserProfile


ROLE_ENTREPRENEUR = UserProfile.ROLE_ENTREPRENEUR
ROLE_INVESTOR = UserProfile.ROLE_INVESTOR
ROLE_GENERAL_PUBLIC = UserProfile.ROLE_GENERAL_PUBLIC
ROLE_ANALYST = UserProfile.ROLE_ANALYST
ROLE_ADMIN = UserProfile.ROLE_ADMIN

ROLE_CHOICES = list(UserProfile.ROLE_CHOICES)
ROLE_CHOICES_REGISTRATION = [choice for choice in ROLE_CHOICES if choice[0] != ROLE_ADMIN]


def normalize_role(value: str | None) -> str:
    role = str(value or "").strip().lower()
    valid = {choice[0] for choice in ROLE_CHOICES}
    if role in valid:
        return role
    return ROLE_GENERAL_PUBLIC


def get_or_create_profile_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": ROLE_GENERAL_PUBLIC},
        )
        return profile
    except (OperationalError, ProgrammingError):
        # Migration not applied yet in this environment.
        return None


def get_user_role(user) -> str:
    if not user or not getattr(user, "is_authenticated", False):
        return ROLE_GENERAL_PUBLIC
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return ROLE_ADMIN
    profile = get_or_create_profile_for_user(user)
    if profile is None:
        return ROLE_GENERAL_PUBLIC
    return normalize_role(profile.role)


ROLE_UI_TEXT_KEYS = {
    ROLE_ENTREPRENEUR: "role_entrepreneur",
    ROLE_INVESTOR: "role_investor",
    ROLE_GENERAL_PUBLIC: "role_general_public",
    ROLE_ANALYST: "role_analyst",
    ROLE_ADMIN: "role_admin",
}


def role_label(role: str, ui_text: dict | None = None) -> str:
    role = normalize_role(role)
    if ui_text:
        key = ROLE_UI_TEXT_KEYS.get(role)
        if key and ui_text.get(key):
            return ui_text[key]
    labels = dict(ROLE_CHOICES)
    return labels.get(role, labels.get(ROLE_GENERAL_PUBLIC, "General public"))


def translated_role_choices(choices, ui_text: dict | None = None):
    if not ui_text:
        return list(choices)
    return [
        (code, ui_text.get(ROLE_UI_TEXT_KEYS.get(code), fallback_label))
        for code, fallback_label in choices
    ]


def role_home_url_name(role: str) -> str:
    role = normalize_role(role)
    if role == ROLE_INVESTOR:
        return "investor_dashboard"
    if role == ROLE_ENTREPRENEUR:
        return "dashboard"
    if role == ROLE_GENERAL_PUBLIC:
        return "public_ideas"
    if role == ROLE_ANALYST:
        return "dashboard"
    if role == ROLE_ADMIN:
        return "dashboard"
    return "dashboard"


def role_home_url(role: str) -> str:
    return reverse(role_home_url_name(role))


def role_access_matrix(role: str) -> dict:
    role = normalize_role(role)
    is_admin = role == ROLE_ADMIN
    is_analyst = role == ROLE_ANALYST
    is_entrepreneur = role == ROLE_ENTREPRENEUR
    is_investor = role == ROLE_INVESTOR
    is_general_public = role == ROLE_GENERAL_PUBLIC

    can_pitch = is_admin or is_analyst or is_entrepreneur
    can_investor = is_admin or is_analyst or is_investor
    can_models = is_admin or is_analyst
    can_model_admin_actions = is_admin
    can_dashboard = is_admin or is_analyst or is_entrepreneur
    can_idea_builder = can_pitch
    can_connections = is_admin or is_analyst or is_investor or is_entrepreneur
    can_public_ideas = is_general_public or is_admin

    return {
        "is_admin": is_admin,
        "is_analyst": is_analyst,
        "is_entrepreneur": is_entrepreneur,
        "is_investor": is_investor,
        "is_general_public": is_general_public,
        "can_dashboard": can_dashboard,
        "can_pitch": can_pitch,
        "can_idea_builder": can_idea_builder,
        "can_investor": can_investor,
        "can_models": can_models,
        "can_model_admin_actions": can_model_admin_actions,
        "can_connections": can_connections,
        "can_public_ideas": can_public_ideas,
    }
