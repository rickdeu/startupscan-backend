from django.contrib.auth.models import Group
from django.urls import reverse_lazy

from superadmin.forms import GroupForm

from .base import (
    BaseSuperadminCreateView,
    BaseSuperadminDeleteView,
    BaseSuperadminDetailView,
    BaseSuperadminListView,
    BaseSuperadminUpdateView,
)


class GroupListView(BaseSuperadminListView):
    model = Group
    template_name = "superadmin/group_list.html"
    context_object_name = "groups"
    search_fields = ("name",)
    ordering = ["name"]


class GroupDetailView(BaseSuperadminDetailView):
    model = Group
    template_name = "superadmin/group_detail.html"
    context_object_name = "group"


class GroupCreateView(BaseSuperadminCreateView):
    model = Group
    form_class = GroupForm
    template_name = "superadmin/group_form.html"
    success_url = reverse_lazy("superadmin:group_list")
    success_message = "Group created successfully."


class GroupUpdateView(BaseSuperadminUpdateView):
    model = Group
    form_class = GroupForm
    template_name = "superadmin/group_form.html"
    success_url = reverse_lazy("superadmin:group_list")
    success_message = "Group updated successfully."


class GroupDeleteView(BaseSuperadminDeleteView):
    model = Group
    success_url = reverse_lazy("superadmin:group_list")
    success_message = "Group deleted successfully."
