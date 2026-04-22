import json
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Max
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from startupscan_api.models import PitchAnalysis
from startupscan_api.roles import (
    ROLE_ADMIN,
    ROLE_ANALISTA,
    ROLE_EMPREENDEDOR,
    get_user_role,
    role_access_matrix,
    role_home_url_name,
)
from .helpers import _list_available_models, _redirect_for_role
from .mixins import RoleRequiredMixin

logger = logging.getLogger(__name__)


class LandingView(View):
    def get(self, request):
        if request.user.is_authenticated:
            role = get_user_role(request.user)
            return redirect(role_home_url_name(role))

        basic_monthly = basic_annual = pro_monthly = pro_annual = None
        try:
            from subscriptions.models import SubscriptionPlan
            all_plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_usd'))
            for p in all_plans:
                if p.tier == SubscriptionPlan.TIER_BASIC and p.interval == SubscriptionPlan.INTERVAL_MONTH:
                    basic_monthly = p
                elif p.tier == SubscriptionPlan.TIER_BASIC and p.interval == SubscriptionPlan.INTERVAL_YEAR:
                    basic_annual = p
                elif p.tier == SubscriptionPlan.TIER_PRO and p.interval == SubscriptionPlan.INTERVAL_MONTH:
                    pro_monthly = p
                elif p.tier == SubscriptionPlan.TIER_PRO and p.interval == SubscriptionPlan.INTERVAL_YEAR:
                    pro_annual = p
        except Exception:
            pass

        return render(request, 'analyzer/landing.html', {
            'basic_monthly': basic_monthly,
            'basic_annual': basic_annual,
            'pro_monthly': pro_monthly,
            'pro_annual': pro_annual,
        })


class DashboardView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_EMPREENDEDOR, ROLE_ANALISTA, ROLE_ADMIN}

    def get(self, request):
        role = get_user_role(request.user)

        try:
            min_score = float(request.GET.get("min_score", 0) or 0)
        except ValueError:
            min_score = 0.0
        try:
            max_score = float(request.GET.get("max_score", 10) or 10)
        except ValueError:
            max_score = 10.0
        try:
            days = int(request.GET.get("days", 90) or 90)
        except ValueError:
            days = 90

        engine = str(request.GET.get("engine", "all")).strip().lower()
        if engine not in {"all", "local", "gpt"}:
            engine = "all"

        min_score = max(0.0, min(10.0, min_score))
        max_score = max(0.0, min(10.0, max_score))
        if max_score < min_score:
            max_score = min_score

        all_scored = PitchAnalysis.objects.exclude(success_score__isnull=True)
        if request.user.is_authenticated and role == ROLE_EMPREENDEDOR:
            all_scored = all_scored.filter(user=request.user)
        if days > 0:
            all_scored = all_scored.filter(created_at__gte=timezone.now() - timedelta(days=days))
        if engine != "all":
            all_scored = all_scored.filter(metadata__analysis_engine_requested=engine)
        all_scored = all_scored.filter(success_score__gte=min_score, success_score__lte=max_score)

        if not request.user.is_authenticated:
            recent_analyses = PitchAnalysis.objects.none()
        else:
            recent_qs = (
                PitchAnalysis.objects.filter(user=request.user, success_score__isnull=False)
                .filter(success_score__gte=min_score, success_score__lte=max_score)
            )
            if engine != "all":
                recent_qs = recent_qs.filter(metadata__analysis_engine_requested=engine)
            recent_analyses = recent_qs.order_by('-created_at')[:8]

        global_stats = all_scored.aggregate(
            avg_score=Avg("success_score"),
            total=Count("id"),
            best=Max("success_score"),
        )
        models = _list_available_models()
        active_model = next((m for m in models if m["is_active"]), None)

        history = list(all_scored.order_by("-created_at")[:24])
        history.reverse()
        chart_labels = [f"#{item.id}" for item in history]
        chart_ids = [item.id for item in history]
        chart_scores = [float(item.success_score or 0) for item in history]
        chart_revenues = [float(item.revenue or 0) for item in history]
        chart_growth = [float(item.growth_rate or 0) for item in history]
        score_distribution = [
            all_scored.filter(success_score__lt=5).count(),
            all_scored.filter(success_score__gte=5, success_score__lt=7.5).count(),
            all_scored.filter(success_score__gte=7.5).count(),
        ]

        industry_labels_map = dict(PitchAnalysis.INDUSTRY_CHOICES)
        sector_rows = list(
            all_scored.values("industry")
            .annotate(avg_score=Avg("success_score"), total=Count("id"))
            .order_by("-avg_score")
        )
        sector_labels = [industry_labels_map.get(row["industry"], row["industry"]) for row in sector_rows]
        sector_avg_scores = [round(float(row["avg_score"] or 0), 2) for row in sector_rows]
        sector_totals = [int(row["total"] or 0) for row in sector_rows]

        user_sector_comparison = {}
        if request.user.is_authenticated and recent_analyses:
            latest = recent_analyses[0]
            sector_avg = (
                all_scored.filter(industry=latest.industry)
                .aggregate(avg=Avg("success_score"))
                .get("avg") or 0
            )
            user_sector_comparison = {
                "industry_label": industry_labels_map.get(latest.industry, latest.industry),
                "latest_score": round(float(latest.success_score or 0), 2),
                "sector_avg": round(float(sector_avg), 2),
            }

        return render(request, 'analyzer/dashboard.html', {
            'recent_analyses': recent_analyses,
            'global_stats': global_stats,
            'active_model': active_model,
            'models_count': len(models),
            'chart_labels_json': json.dumps(chart_labels),
            'chart_ids_json': json.dumps(chart_ids),
            'chart_scores_json': json.dumps(chart_scores),
            'chart_revenues_json': json.dumps(chart_revenues),
            'chart_growth_json': json.dumps(chart_growth),
            'chart_distribution_json': json.dumps(score_distribution),
            'chart_sector_labels_json': json.dumps(sector_labels),
            'chart_sector_avg_json': json.dumps(sector_avg_scores),
            'chart_sector_total_json': json.dumps(sector_totals),
            'filter_min_score': min_score,
            'filter_max_score': max_score,
            'filter_days': days,
            'filter_engine': engine,
            'user_sector_comparison': user_sector_comparison,
            'role_access': role_access_matrix(role),
        })
