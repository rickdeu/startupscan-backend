from django.urls import reverse_lazy

from startupscan_api.models import PitchAnalysis
from superadmin.forms import PitchAnalysisForm

from .base import (
    BaseSuperadminCreateView,
    BaseSuperadminDeleteView,
    BaseSuperadminDetailView,
    BaseSuperadminListView,
    BaseSuperadminUpdateView,
)


class PitchAnalysisListView(BaseSuperadminListView):
    model = PitchAnalysis
    template_name = "superadmin/pitch_list.html"
    context_object_name = "analyses"
    search_fields = ("startup_name", "user__username", "contact_email")

    def get_queryset(self):
        qs = super().get_queryset().select_related("user").order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = PitchAnalysis.STATUS_CHOICES
        context["selected_status"] = self.request.GET.get("status", "")
        return context


class PitchAnalysisDetailView(BaseSuperadminDetailView):
    model = PitchAnalysis
    template_name = "superadmin/pitch_detail.html"
    context_object_name = "analysis"

    def get_queryset(self):
        return super().get_queryset().select_related("user")


class PitchAnalysisCreateView(BaseSuperadminCreateView):
    model = PitchAnalysis
    form_class = PitchAnalysisForm
    template_name = "superadmin/pitch_form.html"
    success_url = reverse_lazy("superadmin:pitch_list")
    success_message = "Pitch analysis created successfully."


class PitchAnalysisUpdateView(BaseSuperadminUpdateView):
    model = PitchAnalysis
    form_class = PitchAnalysisForm
    template_name = "superadmin/pitch_form.html"
    success_url = reverse_lazy("superadmin:pitch_list")
    success_message = "Pitch analysis updated successfully."


class PitchAnalysisDeleteView(BaseSuperadminDeleteView):
    model = PitchAnalysis
    success_url = reverse_lazy("superadmin:pitch_list")
    success_message = "Pitch analysis deleted successfully."
