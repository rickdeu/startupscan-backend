from django.urls import reverse_lazy

from superadmin.models import ActivityLog

from .base import BaseSuperadminDeleteView, BaseSuperadminDetailView, BaseSuperadminListView


class ActivityLogDetailView(BaseSuperadminDetailView):
    model = ActivityLog
    template_name = "superadmin/activity_detail.html"
    context_object_name = "log"

    def get_queryset(self):
        return super().get_queryset().select_related("user")


class ActivityLogListView(BaseSuperadminListView):
    model = ActivityLog
    template_name = "superadmin/activity_list.html"
    context_object_name = "logs"
    search_fields = ("user__username", "target_repr")

    def get_queryset(self):
        qs = super().get_queryset().select_related("user").order_by("-created_at")
        action = self.request.GET.get("action", "").strip()
        if action:
            qs = qs.filter(action=action)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_choices"] = ActivityLog.ACTION_CHOICES
        context["selected_action"] = self.request.GET.get("action", "")
        return context


class ActivityLogDeleteView(BaseSuperadminDeleteView):
    model = ActivityLog
    success_url = reverse_lazy("superadmin:activity_list")
    success_message = "Log entry deleted successfully."
