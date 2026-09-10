import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from django.views.generic import TemplateView

from startupscan_api.models import IdeaPitchSubmission, PitchAnalysis
from subscriptions.models import Subscription, SubscriptionPlan
from superadmin.mixins import SuperuserRequiredMixin
from superadmin.models import ActivityLog

PERIODS = {
    "daily": {"days": 14, "trunc": TruncDate, "fmt": "%d/%m"},
    "weekly": {"days": 12 * 7, "trunc": TruncWeek, "fmt": "%d/%m"},
    "monthly": {"days": 365, "trunc": TruncMonth, "fmt": "%b/%y"},
}


class DashboardView(SuperuserRequiredMixin, TemplateView):
    template_name = "superadmin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        action_labels_map = dict(ActivityLog.ACTION_CHOICES)

        periods_data = {}
        for key, cfg in PERIODS.items():
            since = now - timedelta(days=cfg["days"])
            trunc_fn = cfg["trunc"]

            analyses_trend = list(
                PitchAnalysis.objects.filter(created_at__gte=since)
                .annotate(bucket=trunc_fn("created_at"))
                .values("bucket").annotate(total=Count("id")).order_by("bucket")
            )
            action_rows = list(
                ActivityLog.objects.filter(created_at__gte=since)
                .values("action").annotate(total=Count("id")).order_by("-total")
            )

            periods_data[key] = {
                "new_users": User.objects.filter(date_joined__gte=since).count(),
                "new_analyses": PitchAnalysis.objects.filter(created_at__gte=since).count(),
                "new_ideas": IdeaPitchSubmission.objects.filter(created_at__gte=since).count(),
                "operations": ActivityLog.objects.filter(created_at__gte=since).count(),
                "trend_labels": [row["bucket"].strftime(cfg["fmt"]) for row in analyses_trend],
                "trend_totals": [row["total"] for row in analyses_trend],
                "action_labels": [action_labels_map.get(r["action"], r["action"]) for r in action_rows],
                "action_totals": [r["total"] for r in action_rows],
            }

        mrr = 0.0
        for sub in Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).select_related("plan"):
            if not sub.plan:
                continue
            if sub.plan.interval == SubscriptionPlan.INTERVAL_YEAR:
                mrr += float(sub.plan.price_usd) / 12
            elif sub.plan.interval == SubscriptionPlan.INTERVAL_MONTH:
                mrr += float(sub.plan.price_usd)

        recent_activity = list(ActivityLog.objects.select_related("user").order_by("-created_at")[:10])

        context.update({
            "total_users": User.objects.count(),
            "superusers_count": User.objects.filter(is_superuser=True).count(),
            "total_analyses": PitchAnalysis.objects.count(),
            "active_subscriptions": Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).count(),
            "mrr_estimate": round(mrr, 2),
            "total_operations": ActivityLog.objects.count(),
            "periods_json": json.dumps(periods_data),
            "recent_activity": recent_activity,
        })
        return context
