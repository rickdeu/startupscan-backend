from django.urls import reverse_lazy

from startupscan_api.models import PromptTemplate
from superadmin.forms import PromptTemplateForm

from .base import (
    BaseSuperadminCreateView,
    BaseSuperadminDeleteView,
    BaseSuperadminDetailView,
    BaseSuperadminListView,
    BaseSuperadminUpdateView,
)


class PromptTemplateListView(BaseSuperadminListView):
    model = PromptTemplate
    template_name = "superadmin/prompt_list.html"
    context_object_name = "prompts"
    search_fields = ("engine", "purpose")


class PromptTemplateDetailView(BaseSuperadminDetailView):
    model = PromptTemplate
    template_name = "superadmin/prompt_detail.html"
    context_object_name = "prompt"


class PromptTemplateCreateView(BaseSuperadminCreateView):
    model = PromptTemplate
    form_class = PromptTemplateForm
    template_name = "superadmin/prompt_form.html"
    success_url = reverse_lazy("superadmin:prompt_list")
    success_message = "Prompt template created successfully."

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PromptTemplateUpdateView(BaseSuperadminUpdateView):
    model = PromptTemplate
    form_class = PromptTemplateForm
    template_name = "superadmin/prompt_form.html"
    success_url = reverse_lazy("superadmin:prompt_list")
    success_message = "Prompt template updated successfully."

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PromptTemplateDeleteView(BaseSuperadminDeleteView):
    model = PromptTemplate
    success_url = reverse_lazy("superadmin:prompt_list")
    success_message = "Prompt template deleted successfully."
