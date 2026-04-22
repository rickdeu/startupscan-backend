import json
import logging
from datetime import timedelta

from django.db.models import Avg, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from startupscan_api.models import InvestorConnectionInterest, PitchAnalysis
from startupscan_api.roles import (
    ROLE_ADMIN,
    ROLE_ANALISTA,
    ROLE_EMPREENDEDOR,
    ROLE_INVESTIDOR,
    get_user_role,
)
from startupscan_api.services.model_registry import get_active_model_name
from .helpers import _redirect_back_or_default
from .mixins import RoleRequiredMixin
from subscriptions.mixins import SubscriptionGate, check_feature_access, check_limit_access

logger = logging.getLogger(__name__)

INTEREST_STATUS_LABELS = dict(InvestorConnectionInterest.STATUS_CHOICES)


class InvestorDashboardView(SubscriptionGate, RoleRequiredMixin, View):
    allowed_roles = {ROLE_INVESTIDOR, ROLE_ANALISTA, ROLE_ADMIN}
    required_feature = 'investor_dashboard'

    def get(self, request):
        user_role = get_user_role(request.user)
        try:
            min_score = float(request.GET.get("min_score", 0) or 0)
        except ValueError:
            min_score = 0.0
        try:
            max_score = float(request.GET.get("max_score", 10) or 10)
        except ValueError:
            max_score = 10.0
        try:
            days = int(request.GET.get("days", 180) or 180)
        except ValueError:
            days = 180

        engine = str(request.GET.get("engine", "all")).strip().lower()
        if engine not in {"all", "local", "gpt"}:
            engine = "all"

        min_score = max(0.0, min(10.0, min_score))
        max_score = max(0.0, min(10.0, max_score))
        if max_score < min_score:
            max_score = min_score

        analyses = PitchAnalysis.objects.exclude(success_score__isnull=True)
        if days > 0:
            analyses = analyses.filter(created_at__gte=timezone.now() - timedelta(days=days))
        if engine != "all":
            analyses = analyses.filter(metadata__analysis_engine_requested=engine)
        analyses = analyses.filter(success_score__gte=min_score, success_score__lte=max_score).order_by("-created_at")
        top_analyses = list(analyses[:12])

        for analysis in top_analyses:
            report = analysis.report or {}
            investor_pitch = report.get("investor_pitch", {}) if isinstance(report, dict) else {}
            if not investor_pitch:
                score = float(analysis.success_score or 0.0)
                thesis = "Oportunidade em monitoramento"
                if score >= 8:
                    thesis = "Tese de alto crescimento com potencial de escala acelerada"
                elif score >= 6:
                    thesis = "Tese com boa tração e espaço para ganho de eficiência"
                investor_pitch = {
                    "investment_thesis": thesis,
                    "funding_readiness": "Alta" if score >= 7.5 else ("Média" if score >= 5 else "Inicial"),
                    "capital_use_plan": [
                        "Expansão comercial orientada por dados",
                        "Fortalecimento de produto e retenção de clientes",
                        "Otimização de operações e margem",
                    ],
                }
            analysis.investor_pitch = investor_pitch

        interest_by_analysis = {}
        if request.user.is_authenticated and top_analyses:
            analysis_ids = [item.id for item in top_analyses]
            existing = InvestorConnectionInterest.objects.filter(
                investor=request.user, analysis_id__in=analysis_ids
            )
            interest_by_analysis = {item.analysis_id: item for item in existing}
            for analysis in top_analyses:
                analysis.user_interest = interest_by_analysis.get(analysis.id)
                analysis.user_interest_status_label = (
                    INTEREST_STATUS_LABELS.get(analysis.user_interest.status, analysis.user_interest.status)
                    if getattr(analysis, "user_interest", None)
                    else ""
                )

        total = analyses.count()
        summary = analyses.aggregate(avg_score=Avg("success_score"), max_score=Max("success_score"))
        high_potential = analyses.filter(success_score__gte=7.5).count()

        recent_investor = list(analyses[:20])
        investor_labels = [f"#{a.id}" for a in recent_investor]
        investor_ids = [a.id for a in recent_investor]
        investor_scores = [float(a.success_score or 0) for a in recent_investor]
        investor_revenue = [float(a.revenue or 0) for a in recent_investor]
        investor_growth = [float(a.growth_rate or 0) for a in recent_investor]

        return render(request, "analyzer/investor_dashboard.html", {
            "analyses": top_analyses,
            "kpi_total": total,
            "kpi_high_potential": high_potential,
            "kpi_avg_score": round(float(summary["avg_score"] or 0), 2),
            "kpi_max_score": round(float(summary["max_score"] or 0), 2),
            "active_model": get_active_model_name(),
            "investor_labels_json": json.dumps(investor_labels),
            "investor_ids_json": json.dumps(investor_ids),
            "investor_scores_json": json.dumps(investor_scores),
            "investor_revenue_json": json.dumps(investor_revenue),
            "investor_growth_json": json.dumps(investor_growth),
            "filter_min_score": min_score,
            "filter_max_score": max_score,
            "filter_days": days,
            "filter_engine": engine,
            "can_create_interest": user_role in {ROLE_INVESTIDOR, ROLE_ANALISTA, ROLE_ADMIN},
        })


class InvestorInterestCreateView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_INVESTIDOR, ROLE_ANALISTA, ROLE_ADMIN}

    def post(self, request, analysis_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        investor = request.user
        if not investor.is_authenticated:
            return redirect("login")

        if get_user_role(investor) != ROLE_ADMIN:
            allowed, _ = check_limit_access(investor, 'investor_interests_per_month', 'investor_interests_count')
            if not allowed:
                from django.contrib import messages
                messages.warning(request, 'Limite mensal de interesses de investidor atingido. Faça upgrade para continuar.')
                return _redirect_back_or_default(request, 'investor_dashboard')

        if analysis.user_id and analysis.user_id == investor.id:
            from django.contrib import messages
            messages.info(request, "Não é possível demonstrar interesse na sua própria startup.")
            return _redirect_back_or_default(request, "investor_dashboard")

        if not analysis.user_id:
            from django.contrib import messages
            messages.error(request, "Esta análise não possui empreendedor associado para conexão no momento.")
            return _redirect_back_or_default(request, "investor_dashboard")

        investor_message = (request.POST.get("investor_message", "") or "").strip()[:1200]
        interest, created = InvestorConnectionInterest.objects.get_or_create(
            analysis=analysis,
            investor=investor,
            defaults={
                "entrepreneur": analysis.user,
                "status": InvestorConnectionInterest.STATUS_PENDING,
                "investor_message": investor_message,
            },
        )

        from django.contrib import messages
        if created:
            if get_user_role(investor) != ROLE_ADMIN:
                from subscriptions.models import MonthlyUsage
                MonthlyUsage.increment(investor, 'investor_interests_count')
            messages.success(request, "Interesse registado com sucesso. O empreendedor foi notificado no fluxo interno.")
            return _redirect_back_or_default(request, "investor_dashboard")

        changed = False
        if interest.entrepreneur_id != analysis.user_id:
            interest.entrepreneur = analysis.user
            changed = True
        if investor_message and investor_message != interest.investor_message:
            interest.investor_message = investor_message
            changed = True
        if interest.status in {InvestorConnectionInterest.STATUS_REJECTED, InvestorConnectionInterest.STATUS_WITHDRAWN}:
            interest.status = InvestorConnectionInterest.STATUS_PENDING
            interest.entrepreneur_reply = ""
            interest.responded_at = None
            changed = True
        if changed:
            interest.save(update_fields=["entrepreneur", "investor_message", "status", "entrepreneur_reply", "responded_at", "updated_at"])
            messages.success(request, "Interesse atualizado e reenviado para análise do empreendedor.")
        else:
            messages.info(request, "Já existe um interesse ativo para esta startup.")
        return _redirect_back_or_default(request, "investor_dashboard")


class ConnectionInterestUpdateView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_EMPREENDEDOR, ROLE_INVESTIDOR, ROLE_ANALISTA, ROLE_ADMIN}

    def post(self, request, interest_id):
        interest = get_object_or_404(InvestorConnectionInterest, id=interest_id)
        role = get_user_role(request.user)
        action = (request.POST.get("action", "") or "").strip().lower()
        reply = (request.POST.get("entrepreneur_reply", "") or "").strip()[:1200]

        can_manage = role in {ROLE_ADMIN, ROLE_ANALISTA} or (
            role == ROLE_EMPREENDEDOR and interest.entrepreneur_id == request.user.id
        )
        can_withdraw = interest.investor_id == request.user.id or role in {ROLE_ADMIN, ROLE_ANALISTA}

        from django.contrib import messages
        if action == "withdraw" and can_withdraw:
            interest.status = InvestorConnectionInterest.STATUS_WITHDRAWN
            interest.responded_at = timezone.now()
            interest.save(update_fields=["status", "responded_at", "updated_at"])
            messages.success(request, "Interesse retirado com sucesso.")
            return _redirect_back_or_default(request, "connections_hub")

        if can_manage and action in {
            InvestorConnectionInterest.STATUS_REVIEWING,
            InvestorConnectionInterest.STATUS_CONNECTED,
            InvestorConnectionInterest.STATUS_REJECTED,
        }:
            interest.status = action
            if reply:
                interest.entrepreneur_reply = reply
            interest.responded_at = timezone.now()
            interest.save(update_fields=["status", "entrepreneur_reply", "responded_at", "updated_at"])
            messages.success(request, "Status da conexão atualizado.")
            return _redirect_back_or_default(request, "connections_hub")

        messages.error(request, "Não tem permissão para esta ação de conexão.")
        return _redirect_back_or_default(request, "connections_hub")


class ConnectionsHubView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_EMPREENDEDOR, ROLE_INVESTIDOR, ROLE_ANALISTA, ROLE_ADMIN}

    def get(self, request):
        role = get_user_role(request.user)
        qs = InvestorConnectionInterest.objects.select_related(
            "analysis", "investor", "entrepreneur"
        ).order_by("-updated_at")

        if role == ROLE_INVESTIDOR:
            sent_interests = list(qs.filter(investor=request.user))
            received_interests = []
        elif role == ROLE_EMPREENDEDOR:
            sent_interests = list(qs.filter(investor=request.user))
            received_interests = list(qs.filter(entrepreneur=request.user))
        else:
            sent_interests = list(qs)
            received_interests = list(qs)

        return render(request, "analyzer/connections_hub.html", {
            "role": role,
            "sent_interests": sent_interests,
            "received_interests": received_interests,
            "status_labels": INTEREST_STATUS_LABELS,
            "kpi_sent": len(sent_interests),
            "kpi_received": len(received_interests),
            "kpi_connected": len([
                item
                for item in (received_interests if role == ROLE_EMPREENDEDOR else sent_interests)
                if item.status == InvestorConnectionInterest.STATUS_CONNECTED
            ]),
        })
