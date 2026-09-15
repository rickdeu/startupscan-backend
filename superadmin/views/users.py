from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

from superadmin.forms import UserAccountForm, UserPermissionsForm
from superadmin.mixins import SuperuserRequiredMixin

from .base import BaseSuperadminDeleteView, BaseSuperadminDetailView, BaseSuperadminListView


class UserListView(BaseSuperadminListView):
    model = User
    template_name = "superadmin/user_list.html"
    context_object_name = "users"
    search_fields = ("username", "email", "first_name", "last_name")

    def get_queryset(self):
        return super().get_queryset().select_related("profile").order_by("-date_joined")


class UserDetailView(BaseSuperadminDetailView):
    model = User
    template_name = "superadmin/user_detail.html"
    context_object_name = "target"

    def get_queryset(self):
        return super().get_queryset().select_related("profile").prefetch_related("groups", "user_permissions")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from startupscan_api.models import IdeaPitchSubmission, PitchAnalysis

        target = self.object
        context["analyses_count"] = PitchAnalysis.objects.filter(user=target).count()
        context["ideas_count"] = IdeaPitchSubmission.objects.filter(user=target).count()
        try:
            from subscriptions.models import Subscription
            context["subscription"] = Subscription.objects.filter(user=target).select_related("plan").first()
        except Exception:
            context["subscription"] = None
        return context


class UserCreateView(SuperuserRequiredMixin, View):
    template_name = "superadmin/user_form.html"

    def get(self, request):
        form = UserAccountForm()
        return render(request, self.template_name, {"form": form, "creating": True})

    def post(self, request):
        form = UserAccountForm(request.POST, require_password=True)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect("superadmin:user_edit", pk=user.pk)
        return render(request, self.template_name, {"form": form, "creating": True})


class UserEditView(SuperuserRequiredMixin, View):
    template_name = "superadmin/user_form.html"

    def _get_user(self, pk):
        return get_object_or_404(User.objects.select_related("profile"), pk=pk)

    def get(self, request, pk):
        target = self._get_user(pk)
        form = UserAccountForm(instance=target)
        permissions_form = UserPermissionsForm(user=target)
        return render(request, self.template_name, {
            "form": form, "permissions_form": permissions_form, "target": target, "creating": False,
        })

    def post(self, request, pk):
        target = self._get_user(pk)
        if "save_permissions" in request.POST:
            permissions_form = UserPermissionsForm(request.POST, user=target)
            form = UserAccountForm(instance=target)
            if permissions_form.is_valid():
                permissions_form.save()
                messages.success(request, f'Permissions updated for "{target.username}".')
                return redirect("superadmin:user_edit", pk=target.pk)
        else:
            form = UserAccountForm(request.POST, instance=target)
            permissions_form = UserPermissionsForm(user=target)
            if form.is_valid():
                form.save()
                messages.success(request, f'User "{target.username}" updated successfully.')
                return redirect("superadmin:user_edit", pk=target.pk)
        return render(request, self.template_name, {
            "form": form, "permissions_form": permissions_form, "target": target, "creating": False,
        })


class UserDeleteView(BaseSuperadminDeleteView):
    model = User
    template_name = "superadmin/confirm_delete.html"
    success_url = reverse_lazy("superadmin:user_list")
    success_message = "User deleted successfully."

    def get(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            messages.error(request, "You cannot delete your own account.")
            return redirect("superadmin:user_list")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            messages.error(request, "You cannot delete your own account.")
            return redirect("superadmin:user_list")
        return super().post(request, *args, **kwargs)
