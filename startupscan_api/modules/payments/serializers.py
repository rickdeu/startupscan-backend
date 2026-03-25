from rest_framework import serializers

from startupscan_api.modules.subscriptions.constants import (
    SUBSCRIPTION_INTERVAL_CHOICES,
    SUBSCRIPTION_PLAN_CHOICES,
)
from startupscan_api.modules.subscriptions.service import normalize_interval, normalize_plan


class CheckoutRequestSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=SUBSCRIPTION_PLAN_CHOICES, required=True)
    interval = serializers.ChoiceField(choices=SUBSCRIPTION_INTERVAL_CHOICES, required=True)

    def validate(self, attrs):
        attrs["plan"] = normalize_plan(attrs.get("plan"))
        attrs["interval"] = normalize_interval(attrs.get("interval"))
        return attrs
