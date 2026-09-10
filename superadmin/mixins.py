from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class SuperuserRequiredMixin(LoginRequiredMixin):
    """Gate every super-admin view behind ``is_superuser``.

    Staff accounts (``is_staff``) are deliberately NOT enough — this panel is
    for superadmins only, unlike the regular in-app "admin" role.
    """

    login_url = "login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            messages.error(request, "Acesso restrito a superadministradores.")
            return redirect("role_home")
        return super().dispatch(request, *args, **kwargs)
