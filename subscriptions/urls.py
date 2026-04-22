from django.urls import path
from .views import (
    BillingPortalView,
    CheckoutCancelView,
    CheckoutSuccessView,
    CheckoutView,
    PlansView,
    StripeWebhookView,
    SubscriptionStatusView,
)

urlpatterns = [
    path('plans/', PlansView.as_view(), name='subscription_plans'),
    path('checkout/', CheckoutView.as_view(), name='subscription_checkout'),
    path('checkout/success/', CheckoutSuccessView.as_view(), name='subscription_success'),
    path('checkout/cancel/', CheckoutCancelView.as_view(), name='subscription_cancel'),
    path('billing-portal/', BillingPortalView.as_view(), name='subscription_portal'),
    path('webhook/stripe/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('status/', SubscriptionStatusView.as_view(), name='subscription_status'),
]
