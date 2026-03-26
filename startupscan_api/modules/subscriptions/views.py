from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from startupscan_api.models import PaymentTransaction
from startupscan_api.modules.payments.service import sync_all_plans_from_stripe
from startupscan_api.modules.subscriptions.serializers import SubscriptionSummarySerializer
from startupscan_api.modules.subscriptions.service import (
    ensure_trial_for_user,
    get_plan_catalog_payload,
)


class SubscriptionCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Tenta manter catálogo local alinhado ao Stripe antes de responder.
        try:
            sync_all_plans_from_stripe()
        except Exception:
            # Não quebra listagem se Stripe estiver indisponível.
            pass
        return Response(get_plan_catalog_payload(), status=status.HTTP_200_OK)


class SubscriptionMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = ensure_trial_for_user(request.user)
        if not subscription:
            return Response({"detail": "Utilizador não autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

        transactions = PaymentTransaction.objects.filter(subscription=subscription).order_by("-created_at")[:15]
        payload = {
            "subscription": SubscriptionSummarySerializer(subscription).data,
            "recent_payments": [
                {
                    "id": tx.id,
                    "amount_cents": tx.amount_cents,
                    "currency": tx.currency,
                    "status": tx.status,
                    "paid_at": tx.paid_at,
                    "invoice_pdf_url": tx.invoice_pdf_url,
                    "stripe_invoice_id": tx.stripe_invoice_id,
                }
                for tx in transactions
            ],
        }
        return Response(payload, status=status.HTTP_200_OK)


class SubscriptionStartTrialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = ensure_trial_for_user(request.user)
        if not subscription:
            return Response({"detail": "Utilizador não autenticado."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(
            {
                "message": "Trial de 14 dias iniciado com acesso total.",
                "subscription": SubscriptionSummarySerializer(subscription).data,
            },
            status=status.HTTP_200_OK,
        )


class SubscriptionAccessStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = ensure_trial_for_user(request.user)
        if not subscription:
            return Response({"detail": "Utilizador não autenticado."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(
            {
                "has_full_access": subscription.has_full_access,
                "status": subscription.status,
                "plan": subscription.plan,
                "interval": subscription.interval,
                "trial_ends_at": subscription.trial_ends_at,
                "current_period_end": subscription.current_period_end,
                "server_time": timezone.now(),
            },
            status=status.HTTP_200_OK,
        )
