from __future__ import annotations

import os

SUBSCRIPTION_PLAN_BASIC = "basic"
SUBSCRIPTION_PLAN_PRO = "pro"
SUBSCRIPTION_PLAN_CHOICES = (SUBSCRIPTION_PLAN_BASIC, SUBSCRIPTION_PLAN_PRO)

SUBSCRIPTION_INTERVAL_MONTHLY = "monthly"
SUBSCRIPTION_INTERVAL_ANNUAL = "annual"
SUBSCRIPTION_INTERVAL_CHOICES = (
    SUBSCRIPTION_INTERVAL_MONTHLY,
    SUBSCRIPTION_INTERVAL_ANNUAL,
)

TRIAL_DAYS_FULL_ACCESS = 14


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def get_plan_catalog() -> dict:
    return {
        SUBSCRIPTION_PLAN_BASIC: {
            "label": "Basic",
            "description": "Plano essencial para uso regular da plataforma.",
            "prices": {
                SUBSCRIPTION_INTERVAL_MONTHLY: {
                    "amount_cents": _env_int("BASIC_MONTHLY_AMOUNT_CENTS", 2900),
                    "currency": os.getenv("BILLING_CURRENCY", "usd").lower(),
                    "stripe_price_id": str(os.getenv("STRIPE_PRICE_BASIC_MONTHLY", "") or "").strip(),
                },
                SUBSCRIPTION_INTERVAL_ANNUAL: {
                    "amount_cents": _env_int("BASIC_ANNUAL_AMOUNT_CENTS", 29000),
                    "currency": os.getenv("BILLING_CURRENCY", "usd").lower(),
                    "stripe_price_id": str(os.getenv("STRIPE_PRICE_BASIC_ANNUAL", "") or "").strip(),
                },
            },
        },
        SUBSCRIPTION_PLAN_PRO: {
            "label": "Pro",
            "description": "Plano avançado com recursos premium e maior capacidade.",
            "prices": {
                SUBSCRIPTION_INTERVAL_MONTHLY: {
                    "amount_cents": _env_int("PRO_MONTHLY_AMOUNT_CENTS", 7900),
                    "currency": os.getenv("BILLING_CURRENCY", "usd").lower(),
                    "stripe_price_id": str(os.getenv("STRIPE_PRICE_PRO_MONTHLY", "") or "").strip(),
                },
                SUBSCRIPTION_INTERVAL_ANNUAL: {
                    "amount_cents": _env_int("PRO_ANNUAL_AMOUNT_CENTS", 79000),
                    "currency": os.getenv("BILLING_CURRENCY", "usd").lower(),
                    "stripe_price_id": str(os.getenv("STRIPE_PRICE_PRO_ANNUAL", "") or "").strip(),
                },
            },
        },
    }

