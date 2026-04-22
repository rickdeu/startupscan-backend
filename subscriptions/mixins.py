import logging
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from startupscan_api.roles import ROLE_ADMIN, get_user_role

logger = logging.getLogger(__name__)

_REDIRECT_PLANS = 'subscription_plans'


def _get_user_subscription(user):
    try:
        return user.subscription
    except Exception:
        return None


def _get_active_plan(user):
    sub = _get_user_subscription(user)
    if sub is None or not sub.is_active:
        return None, sub
    return sub.plan, sub


def _is_admin(user):
    return get_user_role(user) == ROLE_ADMIN


def _gate_check(user, feature=None, counter=None, usage_field=None):
    """
    Core access check. Returns (allowed: bool, reason: str).
    All public helpers delegate here so the logic lives in one place.
    """
    if _is_admin(user):
        return True, ''

    plan, sub = _get_active_plan(user)

    if sub is None:
        return False, 'no_subscription'
    if not sub.is_active:
        return False, 'subscription_inactive'
    if plan is None:
        return False, 'no_plan'

    if feature and not plan.has_feature(feature):
        return False, f'feature_not_in_plan:{feature}'

    if counter and usage_field:
        from .models import MonthlyUsage
        usage = MonthlyUsage.get_or_create_current(user)
        if not plan.is_within_limit(counter, getattr(usage, usage_field, 0)):
            return False, f'limit_exceeded:{counter}'

    return True, ''


def check_feature_access(user, feature: str) -> tuple[bool, str]:
    return _gate_check(user, feature=feature)


def check_limit_access(user, counter_field: str, usage_field: str) -> tuple[bool, str]:
    return _gate_check(user, counter=counter_field, usage_field=usage_field)


class SubscriptionGate:
    required_feature: str | None = None
    required_counter: str | None = None
    usage_field: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if _is_admin(request.user):
            return super().dispatch(request, *args, **kwargs)

        sub = _get_user_subscription(request.user)
        if sub is None or not sub.is_active:
            messages.warning(request, 'A sua subscrição está inativa. Escolha um plano para continuar.')
            return redirect(_REDIRECT_PLANS)

        allowed, _ = _gate_check(
            request.user,
            feature=self.required_feature,
            counter=self.required_counter,
            usage_field=self.usage_field,
        )
        if not allowed:
            messages.warning(request, 'Esta funcionalidade requer um plano superior. Faça upgrade para aceder.')
            return redirect(_REDIRECT_PLANS)

        return super().dispatch(request, *args, **kwargs)


def subscription_required(feature: str | None = None, counter: str | None = None, usage_field: str | None = None):
    """Decorador para function-based views."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            allowed, reason = _gate_check(request.user, feature=feature, counter=counter, usage_field=usage_field)
            if not allowed:
                msg = 'Subscrição inativa.' if 'subscription' in reason else 'Limite mensal atingido.' if 'limit' in reason else 'Funcionalidade não disponível no seu plano.'
                messages.warning(request, msg)
                return redirect(_REDIRECT_PLANS)

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
