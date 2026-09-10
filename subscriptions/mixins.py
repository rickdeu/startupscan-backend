import logging
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from startupscan_api.engines import AnalysisEngine
from startupscan_api.i18n import build_ui_text, normalize_ui_language
from startupscan_api.roles import ROLE_ADMIN, ROLE_ANALYST, get_user_role

logger = logging.getLogger(__name__)

_REDIRECT_PLANS = 'subscription_plans'


def _ui_text_for_request(request):
    language = normalize_ui_language(
        getattr(request, "ui_language", None) or request.session.get("ui_language")
    )
    return build_ui_text(language)


def _get_user_subscription(user):
    try:
        return user.subscription
    except Exception:
        return None


def _maybe_downgrade_expired_trial(sub):
    """
    No scheduled job processes trial expiry (no Celery beat task is registered
    for it), so a trial that expired without ever converting to a paid plan
    would otherwise leave the user permanently locked out (is_active=False
    forever). Lazily promote it to the Free plan on first access instead.
    """
    if sub is None:
        return sub

    from .models import Subscription, SubscriptionPlan

    if sub.status != Subscription.STATUS_TRIALING:
        return sub
    if sub.trial_end is None or sub.trial_end > timezone.now():
        return sub
    if sub.stripe_subscription_id:
        return sub

    free_plan = SubscriptionPlan.objects.filter(
        tier=SubscriptionPlan.TIER_FREE, is_active=True,
    ).first()
    if free_plan is None:
        return sub

    sub.plan = free_plan
    sub.status = Subscription.STATUS_ACTIVE
    sub.save(update_fields=['plan', 'status', 'updated_at'])
    return sub


def _get_active_plan(user):
    sub = _get_user_subscription(user)
    sub = _maybe_downgrade_expired_trial(sub)
    if sub is None or not sub.is_active:
        return None, sub
    return sub.plan, sub


def _is_admin(user):
    return get_user_role(user) in (ROLE_ADMIN, ROLE_ANALYST)


_ENGINE_FEATURE_MAP = {
    AnalysisEngine.LOCAL: 'local_analysis',
    AnalysisEngine.GPT: 'gpt_analysis',
    AnalysisEngine.DEEPSEEK: 'deepseek_analysis',
    AnalysisEngine.OLLAMA: 'ollama_analysis',
}


def check_engine_access(user, engine: str) -> tuple[bool, str]:
    feature = _ENGINE_FEATURE_MAP.get(engine)
    if feature is None:
        return False, f'unknown_engine:{engine}'
    return _gate_check(user, feature=feature)


def get_available_engines_for_user(user) -> list[str]:
    if _is_admin(user):
        return list(AnalysisEngine.values)
    plan, _sub = _get_active_plan(user)
    if plan is None:
        return []
    return [engine for engine, feature in _ENGINE_FEATURE_MAP.items() if plan.has_feature(feature)]


def pick_default_engine_for_user(user) -> str:
    """Best engine available to the user, preferring depth over speed."""
    available = get_available_engines_for_user(user)
    for candidate in (AnalysisEngine.GPT, AnalysisEngine.DEEPSEEK, AnalysisEngine.OLLAMA, AnalysisEngine.LOCAL):
        if candidate in available:
            return candidate
    return AnalysisEngine.LOCAL


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

        ui_text = _ui_text_for_request(request)

        sub = _maybe_downgrade_expired_trial(_get_user_subscription(request.user))
        if sub is None or not sub.is_active:
            messages.warning(request, ui_text.get(
                'subscription_inactive_choose_plan',
                'Your subscription is inactive. Choose a plan to continue.',
            ))
            return redirect(_REDIRECT_PLANS)

        allowed, _ = _gate_check(
            request.user,
            feature=self.required_feature,
            counter=self.required_counter,
            usage_field=self.usage_field,
        )
        if not allowed:
            messages.warning(request, ui_text.get(
                'feature_requires_upgrade',
                'This feature requires a higher plan. Upgrade to access it.',
            ))
            return redirect(_REDIRECT_PLANS)

        return super().dispatch(request, *args, **kwargs)


def subscription_required(feature: str | None = None, counter: str | None = None, usage_field: str | None = None):
    """Decorator for function-based views."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            allowed, reason = _gate_check(request.user, feature=feature, counter=counter, usage_field=usage_field)
            if not allowed:
                ui_text = _ui_text_for_request(request)
                if 'subscription' in reason:
                    msg = ui_text.get('subscription_inactive_short', 'Inactive subscription.')
                elif 'limit' in reason:
                    msg = ui_text.get('monthly_limit_reached', 'Monthly limit reached.')
                else:
                    msg = ui_text.get('feature_not_in_plan_short', 'Feature not available on your plan.')
                messages.warning(request, msg)
                return redirect(_REDIRECT_PLANS)

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
