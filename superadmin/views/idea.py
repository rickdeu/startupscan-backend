from django.urls import reverse_lazy

from startupscan_api.models import IdeaPitchSubmission, IdeaPublicFeedback
from superadmin.forms import IdeaPitchSubmissionForm, IdeaPublicFeedbackForm

from .base import (
    BaseSuperadminCreateView,
    BaseSuperadminDeleteView,
    BaseSuperadminDetailView,
    BaseSuperadminListView,
    BaseSuperadminUpdateView,
)


class IdeaSubmissionListView(BaseSuperadminListView):
    model = IdeaPitchSubmission
    template_name = "superadmin/idea_list.html"
    context_object_name = "ideas"
    search_fields = ("startup_name", "user__username")

    def get_queryset(self):
        return super().get_queryset().select_related("user").order_by("-created_at")


class IdeaSubmissionDetailView(BaseSuperadminDetailView):
    model = IdeaPitchSubmission
    template_name = "superadmin/idea_detail.html"
    context_object_name = "idea"

    def get_queryset(self):
        return super().get_queryset().select_related("user")


class IdeaSubmissionCreateView(BaseSuperadminCreateView):
    model = IdeaPitchSubmission
    form_class = IdeaPitchSubmissionForm
    template_name = "superadmin/idea_form.html"
    success_url = reverse_lazy("superadmin:idea_list")
    success_message = "Idea pitch created successfully."


class IdeaSubmissionUpdateView(BaseSuperadminUpdateView):
    model = IdeaPitchSubmission
    form_class = IdeaPitchSubmissionForm
    template_name = "superadmin/idea_form.html"
    success_url = reverse_lazy("superadmin:idea_list")
    success_message = "Idea pitch updated successfully."


class IdeaSubmissionDeleteView(BaseSuperadminDeleteView):
    model = IdeaPitchSubmission
    success_url = reverse_lazy("superadmin:idea_list")
    success_message = "Idea pitch deleted successfully."


class IdeaFeedbackListView(BaseSuperadminListView):
    model = IdeaPublicFeedback
    template_name = "superadmin/idea_feedback_list.html"
    context_object_name = "feedbacks"
    search_fields = ("submission__startup_name", "user__username", "comment")

    def get_queryset(self):
        return super().get_queryset().select_related("submission", "user").order_by("-created_at")


class IdeaFeedbackDetailView(BaseSuperadminDetailView):
    model = IdeaPublicFeedback
    template_name = "superadmin/idea_feedback_detail.html"
    context_object_name = "feedback"

    def get_queryset(self):
        return super().get_queryset().select_related("submission", "user")


class IdeaFeedbackCreateView(BaseSuperadminCreateView):
    model = IdeaPublicFeedback
    form_class = IdeaPublicFeedbackForm
    template_name = "superadmin/idea_feedback_form.html"
    success_url = reverse_lazy("superadmin:idea_feedback_list")
    success_message = "Feedback created successfully."


class IdeaFeedbackUpdateView(BaseSuperadminUpdateView):
    model = IdeaPublicFeedback
    form_class = IdeaPublicFeedbackForm
    template_name = "superadmin/idea_feedback_form.html"
    success_url = reverse_lazy("superadmin:idea_feedback_list")
    success_message = "Feedback updated successfully."


class IdeaFeedbackDeleteView(BaseSuperadminDeleteView):
    model = IdeaPublicFeedback
    success_url = reverse_lazy("superadmin:idea_feedback_list")
    success_message = "Feedback deleted successfully."
