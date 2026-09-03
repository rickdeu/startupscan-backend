import json
import logging

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from startupscan_api.i18n import build_ui_text, normalize_ui_language
from .models import Subscription, SubscriptionPlan
from .stripe_sync import (
    create_checkout_session,
    create_portal_session,
    handle_stripe_event,
    sync_plan_to_stripe,
)

logger = logging.getLogger(__name__)


def _get_ui_text(request):
    lang = getattr(request, 'ui_language', None) or request.session.get('ui_language')
    return build_ui_text(normalize_ui_language(lang))


class PlansView(View):
    """Public page listing the available plans."""

    def get(self, request):
        all_plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_usd'))

        def _pick(tier, interval=None):
            for p in all_plans:
                if p.tier == tier and (interval is None or p.interval == interval):
                    return p
            return None

        trial = _pick(SubscriptionPlan.TIER_TRIAL)
        basic_monthly = _pick(SubscriptionPlan.TIER_BASIC, SubscriptionPlan.INTERVAL_MONTH)
        basic_annual = _pick(SubscriptionPlan.TIER_BASIC, SubscriptionPlan.INTERVAL_YEAR)
        pro_monthly = _pick(SubscriptionPlan.TIER_PRO, SubscriptionPlan.INTERVAL_MONTH)
        pro_annual = _pick(SubscriptionPlan.TIER_PRO, SubscriptionPlan.INTERVAL_YEAR)

        user_subscription = None
        user_plan_tier = None
        if request.user.is_authenticated:
            user_subscription = getattr(request.user, 'subscription', None)
            user_plan_tier = user_subscription.plan_tier if user_subscription else None

        return render(request, 'subscriptions/plans.html', {
            'trial': trial,
            'basic_monthly': basic_monthly,
            'basic_annual': basic_annual,
            'pro_monthly': pro_monthly,
            'pro_annual': pro_annual,
            'user_subscription': user_subscription,
            'user_plan_tier': user_plan_tier,
            'ui_text': _get_ui_text(request),
        })


class CheckoutView(LoginRequiredMixin, View):
    """Starts the Stripe Checkout payment flow."""

    def post(self, request):
        ui = _get_ui_text(request)
        plan_id = request.POST.get('plan_id')
        if not plan_id:
            messages.error(request, ui.get('msg_invalid_plan', 'Plano inválido.'))
            return redirect('subscription_plans')

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            messages.error(request, ui.get('msg_plan_not_found', 'Plano não encontrado.'))
            return redirect('subscription_plans')

        if plan.tier == SubscriptionPlan.TIER_TRIAL:
            messages.info(request, ui.get('msg_trial_auto_activated', 'O trial é ativado automaticamente no registo.'))
            return redirect('subscription_plans')

        if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
            # Fall back to static payment links if Stripe API is not configured
            link_key = f'STRIPE_PAYMENT_LINK_{plan.tier.upper()}'
            payment_link = getattr(settings, link_key, '')
            if payment_link:
                return redirect(payment_link)
            messages.error(request, ui.get('msg_payments_not_configured', 'Pagamentos não configurados. Contacte o suporte.'))
            return redirect('subscription_plans')

        try:
            success_url = request.build_absolute_uri(reverse('subscription_success'))
            cancel_url = request.build_absolute_uri(reverse('subscription_cancel'))
            if not plan.stripe_price_id:
                sync_plan_to_stripe(plan)
                plan.refresh_from_db()
            session = create_checkout_session(request.user, plan, success_url, cancel_url)
            return redirect(session.url)
        except ValueError as exc:
            logger.warning('Checkout indisponível: %s', exc)
            messages.error(
                request,
                ui.get(
                    'msg_checkout_unavailable',
                    'Pagamento indisponível: o plano não está sincronizado com o Stripe ou a chave de API é inválida. Contacte o suporte.',
                ),
            )
            return redirect('subscription_plans')
        except Exception as exc:
            logger.exception('Erro ao criar checkout session')
            messages.error(request, ui.get('msg_checkout_error', 'Erro ao iniciar pagamento. Tente novamente.'))
            return redirect('subscription_plans')


class CheckoutSuccessView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'subscriptions/checkout_success.html', {'ui_text': _get_ui_text(request)})


class CheckoutCancelView(View):
    def get(self, request):
        return render(request, 'subscriptions/checkout_cancel.html', {'ui_text': _get_ui_text(request)})


class BillingPortalView(LoginRequiredMixin, View):
    """Redirects to the Stripe Billing Portal."""

    def get(self, request):
        ui = _get_ui_text(request)
        if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
            messages.error(request, ui.get('msg_portal_unavailable', 'Portal de faturação não disponível.'))
            return redirect('subscription_plans')

        try:
            return_url = request.build_absolute_uri(reverse('subscription_plans'))
            session = create_portal_session(request.user, return_url)
            return redirect(session.url)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('subscription_plans')
        except Exception as exc:
            logger.error('Erro ao criar portal session: %s', exc)
            messages.error(request, ui.get('msg_portal_error', 'Erro ao aceder ao portal. Tente novamente.'))
            return redirect('subscription_plans')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Receives and processes Stripe webhooks."""

    def post(self, request):
        stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

        if not stripe_key:
            return HttpResponse(status=400)

        try:
            stripe.api_key = stripe_key
            payload = request.body
            sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

            if webhook_secret:
                try:
                    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
                except stripe.error.SignatureVerificationError:
                    logger.warning('Webhook Stripe com assinatura inválida')
                    return HttpResponse(status=400)
            else:
                event = json.loads(payload)

            handle_stripe_event(event)
            return HttpResponse(status=200)

        except Exception as exc:
            logger.error('Erro no webhook Stripe: %s', exc)
            return HttpResponse(status=500)


class SubscriptionStatusView(LoginRequiredMixin, View):
    """JSON API with the user's subscription status."""

    def get(self, request):
        sub = getattr(request.user, 'subscription', None)
        if sub is None:
            return JsonResponse({'status': 'none', 'plan': None, 'is_active': False})

        plan_data = None
        if sub.plan:
            plan_data = {
                'id': sub.plan.pk,
                'name': sub.plan.name,
                'tier': sub.plan.tier,
                'interval': sub.plan.interval,
                'price_usd': str(sub.plan.price_usd),
            }

        return JsonResponse({
            'status': sub.status,
            'plan': plan_data,
            'is_active': sub.is_active,
            'trial_days_left': sub.trial_days_left,
            'cancel_at_period_end': sub.cancel_at_period_end,
            'current_period_end': (
                sub.current_period_end.isoformat() if sub.current_period_end else None
            ),
        })
