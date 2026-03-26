from __future__ import annotations

from django.db import OperationalError, ProgrammingError

from startupscan_api.models import UserSubscription
from startupscan_api.modules.subscriptions.constants import SUBSCRIPTION_PLAN_PRO
from startupscan_api.modules.subscriptions.service import ensure_trial_for_user


def _full_access_matrix() -> dict[str, bool]:
    return {
        "can_dashboard": True,
        "can_pitch": True,
        "can_idea_builder": True,
        "can_investor": True,
        "can_models": True,
        "can_connections": True,
        "can_public_ideas": True,
        "can_explainer_video": True,
        "can_profile": True,
    }


def _no_subscription_matrix() -> dict[str, bool]:
    return {
        "can_dashboard": False,
        "can_pitch": False,
        "can_idea_builder": False,
        "can_investor": False,
        "can_models": False,
        "can_connections": False,
        "can_public_ideas": False,
        "can_explainer_video": False,
        "can_profile": True,
    }


def get_subscription_access_matrix(subscription: UserSubscription | None) -> dict[str, bool]:
    if subscription is None:
        return _no_subscription_matrix()

    if subscription.is_trial_active:
        return _full_access_matrix()

    if not subscription.is_active_paid:
        return _no_subscription_matrix()

    if subscription.plan == SUBSCRIPTION_PLAN_PRO:
        return _full_access_matrix()

    # Plano Basic (pago): acesso ao núcleo, sem recursos premium.
    return {
        "can_dashboard": True,
        "can_pitch": True,
        "can_idea_builder": True,
        "can_investor": False,
        "can_models": False,
        "can_connections": False,
        "can_public_ideas": True,
        "can_explainer_video": False,
        "can_profile": True,
    }


def get_subscription_and_access_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None, _no_subscription_matrix()

    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return None, _full_access_matrix()

    try:
        subscription = ensure_trial_for_user(user)
    except (OperationalError, ProgrammingError):
        # Ambiente ainda sem migração aplicada.
        return None, _full_access_matrix()

    return subscription, get_subscription_access_matrix(subscription)


ROUTE_ACCESS_REQUIREMENTS = {
    "dashboard": "can_dashboard",
    "pitch_form": "can_pitch",
    "pitch_results": "can_pitch",
    "pitch_report_pdf": "can_pitch",
    "pitch_investor_pdf": "can_pitch",
    "pitch_explainer_video_generate": "can_explainer_video",
    "pitch_presenter_gender_detect": "can_explainer_video",
    "pitch_explainer_video_progress": "can_explainer_video",
    "idea_pitch_builder": "can_idea_builder",
    "idea_pitch_detail": "can_idea_builder",
    "idea_pitch_pdf": "can_idea_builder",
    "public_idea_detail": "can_public_ideas",
    "public_idea_feedback": "can_public_ideas",
    "investor_dashboard": "can_investor",
    "investor_interest_create": "can_investor",
    "connections_hub": "can_connections",
    "connection_interest_update": "can_connections",
    "model_management": "can_models",
    "model_training_progress": "can_models",
    "user_profile": "can_profile",
}


def is_subscription_allowed_for_route(url_name: str | None, access: dict[str, bool]) -> bool:
    normalized_url_name = str(url_name or "").strip()
    if normalized_url_name == "user_profile":
        # Perfil deve permanecer acessível para qualquer utilizador autenticado.
        return True
    key = ROUTE_ACCESS_REQUIREMENTS.get(normalized_url_name)
    if not key:
        return True
    return bool(access.get(key, False))
