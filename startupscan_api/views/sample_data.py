import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from startupscan_api.i18n import build_ui_text, normalize_ui_language
from startupscan_api.roles import ROLE_ADMIN, ROLE_ANALYST, get_user_role
from .helpers import _redirect_for_role

logger = logging.getLogger(__name__)

# Small, fast batch meant as a quick demo-data helper for admins/analysts —
# the large 1000+ record seeding is still done via the management commands
# directly (seed_demo_analyses / seed_demo_idea_pitches --count N).
SAMPLE_DATA_COUNT = 15


@login_required
@require_POST
def generate_sample_data(request):
    ui_text = build_ui_text(normalize_ui_language(getattr(request, "ui_language", None)))
    role = get_user_role(request.user)
    if role not in (ROLE_ADMIN, ROLE_ANALYST):
        messages.error(request, ui_text.get(
            "msg_role_not_permitted", "Your profile does not have permission to access this page.",
        ))
        return _redirect_for_role(request, fallback_role=role)

    try:
        call_command("seed_demo_analyses", "--count", str(SAMPLE_DATA_COUNT))
        call_command("seed_demo_idea_pitches", "--count", str(SAMPLE_DATA_COUNT))
        messages.success(request, ui_text.get(
            "msg_sample_data_generated",
            "{count} sample records generated successfully.",
        ).format(count=SAMPLE_DATA_COUNT * 2))
    except Exception as exc:
        logger.error("Sample data generation failed: %s", str(exc), exc_info=True)
        messages.error(request, ui_text.get(
            "msg_sample_data_failed", "Failed to generate sample data: {error}",
        ).format(error=str(exc)))

    next_url = (request.POST.get("next") or request.META.get("HTTP_REFERER") or "").strip()
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("dashboard")
    return redirect(next_url)
