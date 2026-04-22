from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import activate
from django.views import View

from startupscan_api.forms import RegisterForm
from startupscan_api.i18n import normalize_ui_language, to_django_language
from startupscan_api.roles import get_or_create_profile_for_user, get_user_role, role_home_url
from .helpers import _redirect_for_role


class RoleBasedLoginView(LoginView):
    template_name = "analyzer/login.html"

    def get_success_url(self):
        role = get_user_role(self.request.user)
        return role_home_url(role)


class RoleHomeView(LoginRequiredMixin, View):
    def get(self, request):
        return _redirect_for_role(request)


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            get_or_create_profile_for_user(user)
            messages.success(request, "Registro realizado com sucesso!")
            return _redirect_for_role(request, fallback_role=get_user_role(user))
    else:
        form = RegisterForm()
    return render(request, 'analyzer/register.html', {'form': form})


def set_ui_language(request):
    if request.method != "POST":
        return redirect("dashboard")

    selected = normalize_ui_language(request.POST.get("language", "pt"))
    django_lang = to_django_language(selected)

    request.session["ui_language"] = selected
    request.session["django_language"] = django_lang
    activate(django_lang)

    next_url = (request.POST.get("next") or request.META.get("HTTP_REFERER") or "").strip()
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("dashboard")

    response = HttpResponseRedirect(next_url)
    response.set_cookie("ui_language", selected, max_age=60 * 60 * 24 * 365, samesite="Lax")
    response.set_cookie("django_language", django_lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response
