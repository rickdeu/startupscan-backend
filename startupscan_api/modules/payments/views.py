from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from startupscan_api.modules.payments.serializers import CheckoutRequestSerializer
from startupscan_api.modules.payments.service import (
    create_checkout_session,
    create_customer_portal_session,
    record_payment_from_invoice_event,
    sync_subscription_from_stripe_data,
)
from startupscan_api.modules.payments.stripe_client import get_stripe_client, get_webhook_secret


class CheckoutSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        session = create_checkout_session(
            request=request,
            user=request.user,
            plan=data["plan"],
            interval=data["interval"],
        )
        return Response(
            {
                "checkout_url": session.get("url"),
                "session_id": session.get("id"),
                "status": "created",
            },
            status=status.HTTP_200_OK,
        )


class CheckoutSuccessView(LoginRequiredMixin, View):
    def get(self, request):
        payload = {
            "message": "Checkout concluído. Aguarde confirmação do pagamento via webhook.",
        }
        return HttpResponse(json.dumps(payload, ensure_ascii=False), content_type="application/json")


class CheckoutCancelView(LoginRequiredMixin, View):
    def get(self, request):
        payload = {
            "message": "Checkout cancelado pelo utilizador.",
        }
        return HttpResponse(json.dumps(payload, ensure_ascii=False), content_type="application/json")


class BillingPortalCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        portal = create_customer_portal_session(request, request.user)
        return Response(
            {
                "portal_url": portal.get("url"),
                "status": "created",
            },
            status=status.HTTP_200_OK,
        )


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        webhook_secret = get_webhook_secret()

        if webhook_secret:
            try:
                stripe_api = get_stripe_client()
                event = stripe_api.Webhook.construct_event(payload, sig_header, webhook_secret)
            except Exception as exc:
                return Response({"detail": f"Webhook inválido: {str(exc)}"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                event = json.loads(payload.decode("utf-8"))
            except Exception:
                return Response({"detail": "JSON inválido no webhook."}, status=status.HTTP_400_BAD_REQUEST)

        event_type = str(event.get("type") or "").strip()
        event_data = (event.get("data") or {}).get("object") or {}

        if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
            sync_subscription_from_stripe_data(event_data)

        if event_type in {"invoice.paid", "invoice.payment_succeeded", "invoice.payment_failed"}:
            record_payment_from_invoice_event(event_data)

        return Response({"received": True}, status=status.HTTP_200_OK)
