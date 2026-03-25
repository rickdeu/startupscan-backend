from __future__ import annotations

import os

import stripe


def get_stripe_client():
    api_key = str(os.getenv("STRIPE_SECRET_KEY", "") or "").strip()
    if not api_key:
        raise ValueError("STRIPE_SECRET_KEY não configurada.")
    stripe.api_key = api_key
    return stripe


def get_webhook_secret() -> str:
    return str(os.getenv("STRIPE_WEBHOOK_SECRET", "") or "").strip()

