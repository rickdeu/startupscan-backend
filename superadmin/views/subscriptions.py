from django.urls import reverse_lazy

from subscriptions.models import MonthlyUsage, Subscription, SubscriptionPlan
from superadmin.forms import MonthlyUsageForm, SubscriptionForm, SubscriptionPlanForm

from .base import (
    BaseSuperadminCreateView,
    BaseSuperadminDeleteView,
    BaseSuperadminDetailView,
    BaseSuperadminListView,
    BaseSuperadminUpdateView,
)


class PlanListView(BaseSuperadminListView):
    model = SubscriptionPlan
    template_name = "superadmin/plan_list.html"
    context_object_name = "plans"
    search_fields = ("name", "tier")
    ordering = ["price_usd"]


class PlanDetailView(BaseSuperadminDetailView):
    model = SubscriptionPlan
    template_name = "superadmin/plan_detail.html"
    context_object_name = "plan"


class PlanCreateView(BaseSuperadminCreateView):
    model = SubscriptionPlan
    form_class = SubscriptionPlanForm
    template_name = "superadmin/plan_form.html"
    success_url = reverse_lazy("superadmin:plan_list")
    success_message = "Plan created successfully."


class PlanUpdateView(BaseSuperadminUpdateView):
    model = SubscriptionPlan
    form_class = SubscriptionPlanForm
    template_name = "superadmin/plan_form.html"
    success_url = reverse_lazy("superadmin:plan_list")
    success_message = "Plan updated successfully."


class PlanDeleteView(BaseSuperadminDeleteView):
    model = SubscriptionPlan
    success_url = reverse_lazy("superadmin:plan_list")
    success_message = "Plan deleted successfully."


class SubscriptionListView(BaseSuperadminListView):
    model = Subscription
    template_name = "superadmin/subscription_list.html"
    context_object_name = "subscriptions"
    search_fields = ("user__username", "user__email", "stripe_customer_id")

    def get_queryset(self):
        return super().get_queryset().select_related("user", "plan").order_by("-created_at")


class SubscriptionDetailView(BaseSuperadminDetailView):
    model = Subscription
    template_name = "superadmin/subscription_detail.html"
    context_object_name = "subscription"

    def get_queryset(self):
        return super().get_queryset().select_related("user", "plan")


class SubscriptionCreateView(BaseSuperadminCreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = "superadmin/subscription_form.html"
    success_url = reverse_lazy("superadmin:subscription_list")
    success_message = "Subscription created successfully."


class SubscriptionUpdateView(BaseSuperadminUpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = "superadmin/subscription_form.html"
    success_url = reverse_lazy("superadmin:subscription_list")
    success_message = "Subscription updated successfully."


class SubscriptionDeleteView(BaseSuperadminDeleteView):
    model = Subscription
    success_url = reverse_lazy("superadmin:subscription_list")
    success_message = "Subscription deleted successfully."


class UsageListView(BaseSuperadminListView):
    model = MonthlyUsage
    template_name = "superadmin/usage_list.html"
    context_object_name = "usages"
    search_fields = ("user__username", "user__email")

    def get_queryset(self):
        return super().get_queryset().select_related("user").order_by("-year", "-month")


class UsageDetailView(BaseSuperadminDetailView):
    model = MonthlyUsage
    template_name = "superadmin/usage_detail.html"
    context_object_name = "usage"

    def get_queryset(self):
        return super().get_queryset().select_related("user")


class UsageCreateView(BaseSuperadminCreateView):
    model = MonthlyUsage
    form_class = MonthlyUsageForm
    template_name = "superadmin/usage_form.html"
    success_url = reverse_lazy("superadmin:usage_list")
    success_message = "Usage record created successfully."


class UsageUpdateView(BaseSuperadminUpdateView):
    model = MonthlyUsage
    form_class = MonthlyUsageForm
    template_name = "superadmin/usage_form.html"
    success_url = reverse_lazy("superadmin:usage_list")
    success_message = "Usage record updated successfully."


class UsageDeleteView(BaseSuperadminDeleteView):
    model = MonthlyUsage
    success_url = reverse_lazy("superadmin:usage_list")
    success_message = "Usage record deleted successfully."
