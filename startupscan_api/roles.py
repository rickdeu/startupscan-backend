from django.urls import reverse
from django.db import OperationalError, ProgrammingError

from startupscan_api.models import UserProfile


ROLE_EMPREENDEDOR = UserProfile.ROLE_EMPREENDEDOR
ROLE_INVESTIDOR = UserProfile.ROLE_INVESTIDOR
ROLE_PUBLICO = UserProfile.ROLE_PUBLICO
ROLE_ANALISTA = UserProfile.ROLE_ANALISTA
ROLE_ADMIN = UserProfile.ROLE_ADMIN

ROLE_CHOICES = list(UserProfile.ROLE_CHOICES)
ROLE_CHOICES_REGISTRATION = [choice for choice in ROLE_CHOICES if choice[0] != ROLE_ADMIN]
ROLE_CHOICES_PUBLIC_REGISTRATION = [
    choice
    for choice in ROLE_CHOICES
    if choice[0] in {ROLE_PUBLICO, ROLE_EMPREENDEDOR, ROLE_INVESTIDOR}
]


def normalize_role(value: str | None) -> str:
    role = str(value or "").strip().lower()
    valid = {choice[0] for choice in ROLE_CHOICES}
    if role in valid:
        return role
    return ROLE_PUBLICO


def get_or_create_profile_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": ROLE_PUBLICO},
        )
        return profile
    except (OperationalError, ProgrammingError):
        # Migração ainda não aplicada no ambiente.
        return None


def get_user_role(user) -> str:
    if not user or not getattr(user, "is_authenticated", False):
        return ROLE_PUBLICO
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return ROLE_ADMIN
    profile = get_or_create_profile_for_user(user)
    if profile is None:
        return ROLE_PUBLICO
    return normalize_role(profile.role)


def role_label(role: str) -> str:
    role = normalize_role(role)
    labels = dict(ROLE_CHOICES)
    return labels.get(role, labels.get(ROLE_PUBLICO, "Público em geral"))


def role_home_url_name(role: str) -> str:
    role = normalize_role(role)
    if role == ROLE_INVESTIDOR:
        return "investor_dashboard"
    if role == ROLE_EMPREENDEDOR:
        return "dashboard"
    if role == ROLE_PUBLICO:
        return "public_ideas"
    if role == ROLE_ANALISTA:
        return "dashboard"
    if role == ROLE_ADMIN:
        return "dashboard"
    return "dashboard"


def role_home_url(role: str) -> str:
    return reverse(role_home_url_name(role))


def role_access_matrix(role: str) -> dict:
    role = normalize_role(role)
    is_admin = role == ROLE_ADMIN
    is_analista = role == ROLE_ANALISTA
    is_empreendedor = role == ROLE_EMPREENDEDOR
    is_investidor = role == ROLE_INVESTIDOR
    is_publico = role == ROLE_PUBLICO

    can_pitch = is_admin or is_analista or is_empreendedor
    can_investor = is_admin or is_analista or is_investidor
    can_models = is_admin or is_analista
    can_model_admin_actions = is_admin
    can_dashboard = is_admin or is_analista or is_empreendedor
    can_idea_builder = can_pitch
    can_connections = is_admin or is_analista or is_investidor or is_empreendedor
    can_public_ideas = is_publico or is_admin or is_empreendedor or is_investidor or is_analista

    return {
        "is_admin": is_admin,
        "is_analista": is_analista,
        "is_empreendedor": is_empreendedor,
        "is_investidor": is_investidor,
        "is_publico": is_publico,
        "can_dashboard": can_dashboard,
        "can_pitch": can_pitch,
        "can_idea_builder": can_idea_builder,
        "can_investor": can_investor,
        "can_models": can_models,
        "can_model_admin_actions": can_model_admin_actions,
        "can_connections": can_connections,
        "can_public_ideas": can_public_ideas,
    }

