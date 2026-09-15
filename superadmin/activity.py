import logging

from .models import ActivityLog

logger = logging.getLogger(__name__)


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_activity(request=None, *, action, user=None, target=None, **metadata):
    """Record one operation in the activity log. Never raises."""
    try:
        actor = user
        if actor is None and request is not None and request.user.is_authenticated:
            actor = request.user
        ActivityLog.objects.create(
            user=actor,
            action=action,
            target_repr=str(target) if target is not None else "",
            metadata=metadata,
            ip_address=_client_ip(request),
        )
    except Exception:
        logger.warning("Failed to record activity log entry for action=%s", action, exc_info=True)
