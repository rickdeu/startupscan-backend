from django.urls import path

from startupscan_api.modules.subscriptions.views import (
    SubscriptionAccessStatusView,
    SubscriptionCatalogView,
    SubscriptionMeView,
    SubscriptionStartTrialView,
)


urlpatterns = [
    path("catalog/", SubscriptionCatalogView.as_view(), name="subscription_catalog"),
    path("me/", SubscriptionMeView.as_view(), name="subscription_me"),
    path("start-trial/", SubscriptionStartTrialView.as_view(), name="subscription_start_trial"),
    path("access-status/", SubscriptionAccessStatusView.as_view(), name="subscription_access_status"),
]
