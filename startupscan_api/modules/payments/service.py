from __future__ import annotations

from datetime import datetime
from datetime import timezone as datetime_timezone

from django.urls import reverse
from django.utils import timezone

from startupscan_api.models import PaymentTransaction, SubscriptionPlan, SubscriptionPlanPrice, UserSubscription
from startupscan_api.modules.payments.stripe_client import get_stripe_client
from startupscan_api.modules.subscriptions.service import (
    get_or_create_user_subscription,
    get_plan_price_config,
    normalize_interval,
    normalize_plan,
)


def _to_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromtimestamp(int(value), tz=datetime_timezone.utc)
    return dt


def _absolute_url(request, url_name: str) -> str:
    return request.build_absolute_uri(reverse(url_name))


def _checkout_urls(request) -> tuple[str, str]:
    success_url = _absolute_url(request, "subscription_checkout_success") + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = _absolute_url(request, "subscription_checkout_cancel")
    return success_url, cancel_url


def _sync_price_from_stripe(price_obj: dict) -> SubscriptionPlanPrice | None:
    stripe_price_id = str(price_obj.get("id") or "").strip()
    if not stripe_price_id:
        return None

    recurring = price_obj.get("recurring") or {}
    recurring_interval = str(recurring.get("interval") or "").strip().lower()
    interval_map = {"month": "monthly", "year": "annual"}
    interval = interval_map.get(recurring_interval, "")
    if not interval:
        return None

    unit_amount = int(price_obj.get("unit_amount") or 0)
    currency = str(price_obj.get("currency") or "usd").lower()

    product_obj = price_obj.get("product")
    if isinstance(product_obj, dict):
        product_id = str(product_obj.get("id") or "").strip()
        product_name = str(product_obj.get("name") or "").strip()
        product_description = str(product_obj.get("description") or "").strip()
        product_metadata = product_obj.get("metadata") or {}
    else:
        product_id = str(product_obj or "").strip()
        product_name = ""
        product_description = ""
        product_metadata = {}

    plan_code_hint = str((product_metadata or {}).get("plan_code") or "").strip().lower()
    if not plan_code_hint:
        lookup_name = product_name.lower()
        if "pro" in lookup_name:
            plan_code_hint = "pro"
        elif "basic" in lookup_name:
            plan_code_hint = "basic"

    if plan_code_hint not in {"basic", "pro"}:
        return None

    plan_defaults = {
        "name": product_name or plan_code_hint.title(),
        "description": product_description,
        "is_active": True,
        "stripe_product_id": product_id,
        "metadata": {"stripe_product_metadata": product_metadata},
    }
    plan, _ = SubscriptionPlan.objects.update_or_create(code=plan_code_hint, defaults=plan_defaults)

    price_defaults = {
        "amount_cents": max(0, unit_amount),
        "currency": currency,
        "is_active": bool(price_obj.get("active", True)),
        "stripe_price_id": stripe_price_id,
        "metadata": {"stripe_price": price_obj},
    }
    db_price, _ = SubscriptionPlanPrice.objects.update_or_create(
        plan=plan,
        interval=interval,
        defaults=price_defaults,
    )
    return db_price


def sync_all_plans_from_stripe() -> list[SubscriptionPlanPrice]:
    stripe_api = get_stripe_client()
    synced: list[SubscriptionPlanPrice] = []
    has_more = True
    starting_after = None

    while has_more:
        kwargs = {"limit": 100, "active": True, "expand": ["data.product"]}
        if starting_after:
            kwargs["starting_after"] = starting_after
        response = stripe_api.Price.list(**kwargs)
        data = list(response.get("data") or [])
        for item in data:
            if str(item.get("type") or "").strip().lower() != "recurring":
                continue
            db_price = _sync_price_from_stripe(item)
            if db_price:
                synced.append(db_price)
        has_more = bool(response.get("has_more"))
        if data:
            starting_after = data[-1].get("id")
        else:
            has_more = False

    return synced


def _ensure_stripe_customer_for_subscription(stripe_api, user, subscription: UserSubscription) -> str:
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    customer = stripe_api.Customer.create(
        email=(user.email or "").strip() or None,
        name=(user.get_full_name() or user.username or "").strip() or None,
        metadata={
            "user_id": str(user.id),
            "username": user.username,
        },
    )
    subscription.stripe_customer_id = customer["id"]
    subscription.save(update_fields=["stripe_customer_id", "updated_at"])
    return subscription.stripe_customer_id


def create_checkout_session(request, user, plan: str, interval: str) -> dict:
    subscription = get_or_create_user_subscription(user)
    if not subscription:
        raise ValueError("Utilizador não autenticado para criar checkout.")

    normalized_plan = normalize_plan(plan)
    normalized_interval = normalize_interval(interval)
    price_cfg = get_plan_price_config(normalized_plan, normalized_interval)
    price_id = str(price_cfg.get("stripe_price_id", "") or "").strip()
    if not price_id:
        raise ValueError("Preço Stripe não configurado no banco para o plano/intervalo selecionado.")

    stripe_api = get_stripe_client()
    success_url, cancel_url = _checkout_urls(request)
    customer_id = _ensure_stripe_customer_for_subscription(stripe_api, user, subscription)

    session = stripe_api.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(user.id),
        metadata={
            "user_id": str(user.id),
            "plan": normalized_plan,
            "interval": normalized_interval,
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "plan": normalized_plan,
                "interval": normalized_interval,
            }
        },
    )

    subscription.plan = normalized_plan
    subscription.interval = normalized_interval
    subscription.status = UserSubscription.STATUS_INCOMPLETE
    subscription.save(update_fields=["plan", "interval", "status", "updated_at"])
    return session


def create_customer_portal_session(request, user) -> dict:
    subscription = get_or_create_user_subscription(user)
    if not subscription or not subscription.stripe_customer_id:
        raise ValueError("Cliente Stripe não encontrado para este utilizador.")

    stripe_api = get_stripe_client()
    return_url = _absolute_url(request, "subscription_me")
    portal = stripe_api.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=return_url,
    )
    return portal


def _map_stripe_status_to_local(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    mapping = {
        "trialing": UserSubscription.STATUS_TRIAL,
        "active": UserSubscription.STATUS_ACTIVE,
        "past_due": UserSubscription.STATUS_PAST_DUE,
        "canceled": UserSubscription.STATUS_CANCELED,
        "incomplete": UserSubscription.STATUS_INCOMPLETE,
        "incomplete_expired": UserSubscription.STATUS_EXPIRED,
        "unpaid": UserSubscription.STATUS_UNPAID,
        "paused": UserSubscription.STATUS_PAUSED,
    }
    return mapping.get(raw, UserSubscription.STATUS_INCOMPLETE)


def sync_subscription_from_stripe_data(stripe_subscription: dict, fallback_user_id: int | None = None):
    metadata = stripe_subscription.get("metadata") or {}
    user_id = metadata.get("user_id") or fallback_user_id
    customer_id = stripe_subscription.get("customer")
    if isinstance(customer_id, dict):
        customer_id = customer_id.get("id")
    customer_id = str(customer_id or "").strip()
    stripe_subscription_id = str(stripe_subscription.get("id") or "").strip()
    if not stripe_subscription_id:
        return None

    from django.contrib.auth.models import User

    subscription = None
    if user_id:
        try:
            normalized_user_id = int(user_id)
        except (TypeError, ValueError):
            normalized_user_id = None
        if normalized_user_id:
            user = User.objects.filter(id=normalized_user_id).first()
            if user:
                subscription = get_or_create_user_subscription(user)
    if subscription is None and customer_id:
        subscription = UserSubscription.objects.filter(stripe_customer_id=customer_id).first()
    if subscription is None:
        return None

    items = ((stripe_subscription.get("items") or {}).get("data") or [])
    first_item = items[0] if items else {}
    price_obj = first_item.get("price") or {}
    stripe_price_id = str(price_obj.get("id") or "").strip()

    db_price = None
    if stripe_price_id:
        db_price = _sync_price_from_stripe(price_obj) if isinstance(price_obj, dict) else None
    if db_price is None and stripe_price_id:
        db_price = (
            SubscriptionPlanPrice.objects.select_related("plan")
            .filter(stripe_price_id=stripe_price_id, is_active=True, plan__is_active=True)
            .first()
        )

    if db_price:
        plan = normalize_plan(db_price.plan.code)
        interval = normalize_interval(db_price.interval)
    else:
        plan = normalize_plan(metadata.get("plan") or subscription.plan)
        interval = normalize_interval(metadata.get("interval") or subscription.interval)
    local_status = _map_stripe_status_to_local(stripe_subscription.get("status"))

    subscription.plan = plan
    subscription.interval = interval
    subscription.status = local_status
    subscription.stripe_customer_id = customer_id or subscription.stripe_customer_id
    subscription.stripe_subscription_id = stripe_subscription_id
    subscription.current_period_start = _to_datetime(stripe_subscription.get("current_period_start"))
    subscription.current_period_end = _to_datetime(stripe_subscription.get("current_period_end"))
    subscription.trial_started_at = _to_datetime(stripe_subscription.get("trial_start"))
    subscription.trial_ends_at = _to_datetime(stripe_subscription.get("trial_end"))
    subscription.cancel_at_period_end = bool(stripe_subscription.get("cancel_at_period_end") or False)
    if stripe_price_id:
        metadata_payload = dict(subscription.metadata or {})
        metadata_payload["stripe_price_id"] = stripe_price_id
        subscription.metadata = metadata_payload
    subscription.save()
    return subscription


def record_payment_from_invoice_event(invoice: dict) -> PaymentTransaction | None:
    subscription_id = invoice.get("subscription")
    if isinstance(subscription_id, dict):
        subscription_id = subscription_id.get("id")
    subscription_id = str(subscription_id or "").strip()
    if not subscription_id:
        return None

    subscription = UserSubscription.objects.filter(stripe_subscription_id=subscription_id).first()
    if subscription is None:
        return None

    amount_paid = int(invoice.get("amount_paid") or 0)
    amount_due = int(invoice.get("amount_due") or 0)
    currency = str(invoice.get("currency") or "usd").lower()
    payment_status = str(invoice.get("status") or "pending").lower()
    hosted_invoice_url = str(invoice.get("hosted_invoice_url") or "").strip()

    invoice_id = str(invoice.get("id") or "").strip()
    payment_intent_id = invoice.get("payment_intent")
    if isinstance(payment_intent_id, dict):
        payment_intent_id = payment_intent_id.get("id")
    payment_intent_id = str(payment_intent_id or "").strip()

    defaults = {
        "subscription": subscription,
        "amount_cents": amount_paid if amount_paid > 0 else amount_due,
        "currency": currency,
        "status": payment_status,
        "stripe_payment_intent_id": payment_intent_id,
        "invoice_pdf_url": hosted_invoice_url,
        "paid_at": _to_datetime(invoice.get("status_transitions", {}).get("paid_at")),
        "metadata": {"invoice": invoice},
    }
    if invoice_id:
        transaction, _ = PaymentTransaction.objects.update_or_create(
            stripe_invoice_id=invoice_id,
            defaults=defaults,
        )
    else:
        transaction = PaymentTransaction.objects.create(stripe_invoice_id=None, **defaults)
    return transaction
