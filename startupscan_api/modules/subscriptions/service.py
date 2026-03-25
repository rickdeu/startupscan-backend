from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from startupscan_api.models import UserSubscription
from startupscan_api.modules.subscriptions.constants import (
    SUBSCRIPTION_INTERVAL_CHOICES,
    SUBSCRIPTION_PLAN_CHOICES,
    TRIAL_DAYS_FULL_ACCESS,
    get_plan_catalog,
)


def normalize_plan(plan: str | None) -> str:
    plan_value = str(plan or "").strip().lower()
    if plan_value in SUBSCRIPTION_PLAN_CHOICES:
        return plan_value
    return SUBSCRIPTION_PLAN_CHOICES[0]


def normalize_interval(interval: str | None) -> str:
    interval_value = str(interval or "").strip().lower()
    if interval_value in SUBSCRIPTION_INTERVAL_CHOICES:
        return interval_value
    return SUBSCRIPTION_INTERVAL_CHOICES[0]


def get_or_create_user_subscription(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    subscription, _ = UserSubscription.objects.get_or_create(user=user)
    return subscription


def start_full_access_trial(subscription: UserSubscription) -> UserSubscription:
    now = timezone.now()
    trial_end = now + timedelta(days=TRIAL_DAYS_FULL_ACCESS)
    subscription.status = UserSubscription.STATUS_TRIAL
    subscription.plan = normalize_plan(subscription.plan)
    subscription.interval = normalize_interval(subscription.interval)
    subscription.trial_started_at = now
    subscription.trial_ends_at = trial_end
    subscription.current_period_start = now
    subscription.current_period_end = trial_end
    subscription.cancel_at_period_end = False
    subscription.save(
        update_fields=[
            "status",
            "plan",
            "interval",
            "trial_started_at",
            "trial_ends_at",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "updated_at",
        ]
    )
    return subscription


def ensure_trial_for_user(user) -> UserSubscription | None:
    subscription = get_or_create_user_subscription(user)
    if not subscription:
        return None
    if subscription.status in {UserSubscription.STATUS_ACTIVE, UserSubscription.STATUS_TRIAL}:
        return subscription
    if subscription.trial_started_at and subscription.trial_ends_at and subscription.trial_ends_at > timezone.now():
        subscription.status = UserSubscription.STATUS_TRIAL
        subscription.current_period_start = subscription.trial_started_at
        subscription.current_period_end = subscription.trial_ends_at
        subscription.save(update_fields=["status", "current_period_start", "current_period_end", "updated_at"])
        return subscription
    return start_full_access_trial(subscription)


def has_full_access(user) -> bool:
    subscription = get_or_create_user_subscription(user)
    if not subscription:
        return False
    return subscription.has_full_access


def get_plan_price_config(plan: str, interval: str) -> dict:
    catalog = get_plan_catalog()
    normalized_plan = normalize_plan(plan)
    normalized_interval = normalize_interval(interval)
    return catalog[normalized_plan]["prices"][normalized_interval]


def get_plan_catalog_payload() -> dict:
    catalog = get_plan_catalog()
    return {
        "trial_days": TRIAL_DAYS_FULL_ACCESS,
        "plans": catalog,
    }
