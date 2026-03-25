from django.urls import path

from startupscan_api.modules.payments.views import (
    BillingPortalCreateView,
    CheckoutCancelView,
    CheckoutSessionCreateView,
    CheckoutSuccessView,
    StripeWebhookView,
)

urlpatterns = [
    path("checkout/", CheckoutSessionCreateView.as_view(), name="subscription_checkout"),
    path("checkout/success/", CheckoutSuccessView.as_view(), name="subscription_checkout_success"),
    path("checkout/cancel/", CheckoutCancelView.as_view(), name="subscription_checkout_cancel"),
    path("portal/", BillingPortalCreateView.as_view(), name="subscription_billing_portal"),
    path("webhook/stripe/", StripeWebhookView.as_view(), name="stripe_webhook"),
]
