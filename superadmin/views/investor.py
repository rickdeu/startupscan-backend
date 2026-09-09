from django.urls import reverse_lazy

from startupscan_api.models import InvestorConnectionInterest
from superadmin.forms import InvestorConnectionInterestForm

from .base import (
    BaseSuperadminCreateView,
    BaseSuperadminDeleteView,
    BaseSuperadminDetailView,
    BaseSuperadminListView,
    BaseSuperadminUpdateView,
)


class InvestorInterestListView(BaseSuperadminListView):
    model = InvestorConnectionInterest
    template_name = "superadmin/investor_interest_list.html"
    context_object_name = "interests"
    search_fields = ("analysis__startup_name", "investor__username", "entrepreneur__username")

    def get_queryset(self):
        return super().get_queryset().select_related("analysis", "investor", "entrepreneur").order_by("-created_at")


class InvestorInterestDetailView(BaseSuperadminDetailView):
    model = InvestorConnectionInterest
    template_name = "superadmin/investor_interest_detail.html"
    context_object_name = "interest"

    def get_queryset(self):
        return super().get_queryset().select_related("analysis", "investor", "entrepreneur")


class InvestorInterestCreateView(BaseSuperadminCreateView):
    model = InvestorConnectionInterest
    form_class = InvestorConnectionInterestForm
    template_name = "superadmin/investor_interest_form.html"
    success_url = reverse_lazy("superadmin:investor_interest_list")
    success_message = "Connection interest created successfully."


class InvestorInterestUpdateView(BaseSuperadminUpdateView):
    model = InvestorConnectionInterest
    form_class = InvestorConnectionInterestForm
    template_name = "superadmin/investor_interest_form.html"
    success_url = reverse_lazy("superadmin:investor_interest_list")
    success_message = "Connection interest updated successfully."


class InvestorInterestDeleteView(BaseSuperadminDeleteView):
    model = InvestorConnectionInterest
    success_url = reverse_lazy("superadmin:investor_interest_list")
    success_message = "Connection interest deleted successfully."
