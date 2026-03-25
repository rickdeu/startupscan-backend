from __future__ import annotations

from rest_framework import serializers

from startupscan_api.models import UserSubscription
from startupscan_api.modules.subscriptions.constants import (
    SUBSCRIPTION_INTERVAL_CHOICES,
    SUBSCRIPTION_PLAN_CHOICES,
)


class SubscriptionCheckoutSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=SUBSCRIPTION_PLAN_CHOICES)
    interval = serializers.ChoiceField(choices=SUBSCRIPTION_INTERVAL_CHOICES)


class SubscriptionSummarySerializer(serializers.ModelSerializer):
    has_full_access = serializers.BooleanField(read_only=True)
    is_trial_active = serializers.BooleanField(read_only=True)
    is_active_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = (
            "id",
            "plan",
            "interval",
            "status",
            "trial_started_at",
            "trial_ends_at",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "stripe_customer_id",
            "stripe_subscription_id",
            "has_full_access",
            "is_trial_active",
            "is_active_paid",
            "created_at",
            "updated_at",
        )

