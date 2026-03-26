from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from startupscan_api.models import SubscriptionPlan, SubscriptionPlanPrice, UserSubscription
from startupscan_api.modules.subscriptions.constants import (
    SUBSCRIPTION_INTERVAL_CHOICES,
    SUBSCRIPTION_PLAN_CHOICES,
    TRIAL_DAYS_FULL_ACCESS,
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
    normalized_plan = normalize_plan(plan)
    normalized_interval = normalize_interval(interval)
    price = (
        SubscriptionPlanPrice.objects.select_related("plan")
        .filter(
            plan__code=normalized_plan,
            interval=normalized_interval,
            is_active=True,
            plan__is_active=True,
        )
        .order_by("id")
        .first()
    )
    if not price:
        raise ValueError("Plano/intervalo não configurado no banco de dados.")
    return {
        "amount_cents": int(price.amount_cents or 0),
        "currency": str(price.currency or "usd").lower(),
        "stripe_price_id": str(price.stripe_price_id or "").strip(),
        "plan_code": price.plan.code,
        "plan_name": price.plan.name,
        "plan_description": price.plan.description,
    }


def get_plan_catalog_payload() -> dict:
    plans = (
        SubscriptionPlan.objects.filter(is_active=True)
        .prefetch_related("prices")
        .order_by("display_order", "name")
    )
    payload_plans = {}
    for plan in plans:
        prices = {item.interval: item for item in plan.prices.filter(is_active=True)}
        payload_plans[plan.code] = {
            "label": plan.name,
            "description": plan.description,
            "stripe_product_id": plan.stripe_product_id,
            "prices": {
                interval: {
                    "amount_cents": int(prices[interval].amount_cents),
                    "currency": str(prices[interval].currency or "usd").lower(),
                    "stripe_price_id": str(prices[interval].stripe_price_id or "").strip(),
                }
                for interval in SUBSCRIPTION_INTERVAL_CHOICES
                if interval in prices
            },
        }
    return {"trial_days": TRIAL_DAYS_FULL_ACCESS, "plans": payload_plans}


def ensure_default_plans_seeded() -> None:
    seed_data = {
        "basic": {
            "name": "Basic",
            "description": "Plano essencial para uso regular da plataforma.",
            "display_order": 10,
            "prices": {
                "monthly": {"amount_cents": 2900, "currency": "usd"},
                "annual": {"amount_cents": 29000, "currency": "usd"},
            },
        },
        "pro": {
            "name": "Pro",
            "description": "Plano avançado com recursos premium e maior capacidade.",
            "display_order": 20,
            "prices": {
                "monthly": {"amount_cents": 7900, "currency": "usd"},
                "annual": {"amount_cents": 79000, "currency": "usd"},
            },
        },
    }
    for plan_code, plan_info in seed_data.items():
        plan, _ = SubscriptionPlan.objects.get_or_create(
            code=plan_code,
            defaults={
                "name": plan_info["name"],
                "description": plan_info["description"],
                "display_order": plan_info["display_order"],
                "is_active": True,
            },
        )
        for interval, price_info in plan_info["prices"].items():
            SubscriptionPlanPrice.objects.get_or_create(
                plan=plan,
                interval=interval,
                defaults={
                    "amount_cents": int(price_info["amount_cents"]),
                    "currency": str(price_info["currency"]).lower(),
                    "is_active": True,
                },
            )
