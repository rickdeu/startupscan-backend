import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_stripe_module = None


def _get_stripe():
    global _stripe_module
    if _stripe_module is not None:
        return _stripe_module
    try:
        import stripe
        key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        if not key:
            return None
        stripe.api_key = key
        _stripe_module = stripe
        return stripe
    except ImportError:
        return None


def sync_plan_to_stripe(plan) -> bool:
    """Cria ou atualiza produto+preço no Stripe para o plano dado."""
    stripe = _get_stripe()
    if not stripe or plan.tier == 'trial' or plan.price_usd == 0:
        return False

    try:
        if plan.stripe_product_id:
            stripe.Product.modify(
                plan.stripe_product_id,
                name=plan.name,
                active=plan.is_active,
                metadata={'tier': plan.tier, 'interval': plan.interval},
            )
        else:
            product = stripe.Product.create(
                name=plan.name,
                metadata={'tier': plan.tier, 'interval': plan.interval},
            )
            plan.stripe_product_id = product.id
            plan.save(update_fields=['stripe_product_id'])

        # Preços no Stripe são imutáveis — só cria um novo se o valor mudou
        needs_new_price = not plan.stripe_price_id
        if not needs_new_price:
            try:
                existing = stripe.Price.retrieve(plan.stripe_price_id)
                needs_new_price = existing.unit_amount != plan.price_cents
            except Exception:
                needs_new_price = True

        if needs_new_price:
            new_price = stripe.Price.create(
                product=plan.stripe_product_id,
                unit_amount=plan.price_cents,
                currency='usd',
                recurring={'interval': plan.interval} if plan.interval in ('month', 'year') else None,
                metadata={'plan_id': str(plan.pk)},
            )
            if plan.stripe_price_id and plan.stripe_price_id != new_price.id:
                try:
                    stripe.Price.modify(plan.stripe_price_id, active=False)
                except Exception as exc:
                    logger.warning('Falha ao arquivar price antigo %s: %s', plan.stripe_price_id, exc)
            plan.stripe_price_id = new_price.id
            plan.save(update_fields=['stripe_price_id'])
        logger.info('Plano %s sincronizado com Stripe (price=%s)', plan.name, plan.stripe_price_id)
        return True

    except Exception as exc:
        logger.error('Falha ao sincronizar plano %s com Stripe: %s', plan.name, exc)
        return False


def create_checkout_session(user, plan, success_url: str, cancel_url: str):
    """Cria uma Stripe Checkout Session para o utilizador assinar o plano."""
    stripe = _get_stripe()
    if not stripe or not plan.stripe_price_id:
        raise ValueError('Stripe não configurado ou plano sem price_id.')

    from .models import Subscription
    subscription = getattr(user, 'subscription', None)
    customer_id = subscription.stripe_customer_id if subscription else None

    session_params = {
        'mode': 'subscription',
        'line_items': [{'price': plan.stripe_price_id, 'quantity': 1}],
        'success_url': success_url,
        'cancel_url': cancel_url,
        'metadata': {'user_id': str(user.pk), 'plan_id': str(plan.pk)},
        'subscription_data': {'metadata': {'user_id': str(user.pk), 'plan_id': str(plan.pk)}},
    }

    if customer_id:
        session_params['customer'] = customer_id
    else:
        session_params['customer_email'] = user.email

    return stripe.checkout.Session.create(**session_params)


def create_portal_session(user, return_url: str):
    """Cria uma Stripe Billing Portal Session para gerir subscrição."""
    stripe = _get_stripe()
    if not stripe:
        raise ValueError('Stripe não configurado.')

    subscription = getattr(user, 'subscription', None)
    customer_id = subscription.stripe_customer_id if subscription else None

    if not customer_id:
        raise ValueError('Utilizador sem customer Stripe.')

    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )


def handle_stripe_event(event) -> bool:
    """Processa um evento Stripe e atualiza a BD."""
    event_type = event.get('type', '')
    data_obj = event.get('data', {}).get('object', {})

    handlers = {
        'checkout.session.completed': _handle_checkout_completed,
        'customer.subscription.created': _handle_subscription_upsert,
        'customer.subscription.updated': _handle_subscription_upsert,
        'customer.subscription.deleted': _handle_subscription_deleted,
        'invoice.payment_succeeded': _handle_invoice_paid,
        'invoice.payment_failed': _handle_invoice_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            handler(data_obj)
            return True
        except Exception as exc:
            logger.error('Erro ao processar evento Stripe %s: %s', event_type, exc)
    return False


def _handle_checkout_completed(session):
    from django.contrib.auth.models import User
    from .models import Subscription, SubscriptionPlan

    user_id = session.get('metadata', {}).get('user_id')
    plan_id = session.get('metadata', {}).get('plan_id')
    customer_id = session.get('customer')
    stripe_sub_id = session.get('subscription')

    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            pass

    if user is None:
        customer_email = session.get('customer_details', {}).get('email') or session.get('customer_email')
        if customer_email:
            user = User.objects.filter(email=customer_email).first()

    if user is None:
        return

    plan = None
    if plan_id:
        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            pass

    sub, _ = Subscription.objects.get_or_create(user=user)
    sub.plan = plan
    sub.status = Subscription.STATUS_ACTIVE
    sub.stripe_customer_id = customer_id or sub.stripe_customer_id
    sub.stripe_subscription_id = stripe_sub_id or sub.stripe_subscription_id
    sub.trial_end = None
    sub.save()

    if plan:
        try:
            from .emails import send_subscription_activated
            send_subscription_activated(user, plan)
        except Exception as exc:
            logger.warning('Falha ao enviar email de ativação: %s', exc)


def _handle_subscription_upsert(stripe_sub):
    from django.contrib.auth.models import User
    from .models import Subscription, SubscriptionPlan

    stripe_sub_id = stripe_sub.get('id')
    customer_id = stripe_sub.get('customer')
    status = stripe_sub.get('status', 'active')
    user_id = stripe_sub.get('metadata', {}).get('user_id')
    plan_id = stripe_sub.get('metadata', {}).get('plan_id')

    sub = None
    if stripe_sub_id:
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first()
    if sub is None and customer_id:
        sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if sub is None and user_id:
        try:
            user = User.objects.get(pk=user_id)
            sub, _ = Subscription.objects.get_or_create(user=user)
        except User.DoesNotExist:
            return

    if sub is None:
        return

    stripe_status_map = {
        'trialing': Subscription.STATUS_TRIALING,
        'active': Subscription.STATUS_ACTIVE,
        'past_due': Subscription.STATUS_PAST_DUE,
        'canceled': Subscription.STATUS_CANCELED,
        'incomplete': Subscription.STATUS_INCOMPLETE,
        'unpaid': Subscription.STATUS_PAST_DUE,
    }
    sub.status = stripe_status_map.get(status, Subscription.STATUS_INACTIVE)
    sub.stripe_customer_id = customer_id or sub.stripe_customer_id
    sub.stripe_subscription_id = stripe_sub_id or sub.stripe_subscription_id
    sub.cancel_at_period_end = stripe_sub.get('cancel_at_period_end', False)

    period_start = stripe_sub.get('current_period_start')
    period_end = stripe_sub.get('current_period_end')
    if period_start:
        sub.current_period_start = timezone.datetime.fromtimestamp(period_start, tz=timezone.utc)
    if period_end:
        sub.current_period_end = timezone.datetime.fromtimestamp(period_end, tz=timezone.utc)

    trial_end_ts = stripe_sub.get('trial_end')
    if trial_end_ts:
        sub.trial_end = timezone.datetime.fromtimestamp(trial_end_ts, tz=timezone.utc)

    old_plan_name = sub.plan.name if sub.plan else None

    if plan_id:
        try:
            sub.plan = SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            pass

    if sub.plan is None:
        items = stripe_sub.get('items', {}).get('data', [])
        if items:
            price_id = items[0].get('price', {}).get('id', '')
            plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
            if plan:
                sub.plan = plan

    sub.save()

    # Notify user when plan changes
    if old_plan_name and sub.plan and old_plan_name != sub.plan.name:
        try:
            from .emails import send_subscription_updated
            send_subscription_updated(sub.user, old_plan_name, sub.plan)
        except Exception as exc:
            logger.warning('Falha ao enviar email de actualização de plano: %s', exc)


def _find_subscription(stripe_sub_id=None, customer_id=None):
    from .models import Subscription
    if stripe_sub_id:
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first()
        if sub:
            return sub
    if customer_id:
        return Subscription.objects.filter(stripe_customer_id=customer_id).first()
    return None


def _handle_subscription_deleted(stripe_sub):
    sub = _find_subscription(stripe_sub.get('id'), stripe_sub.get('customer'))
    if sub:
        from .models import Subscription
        plan_name = sub.plan.name if sub.plan else 'Plano'
        sub.status = Subscription.STATUS_CANCELED
        sub.save(update_fields=['status', 'updated_at'])
        try:
            from .emails import send_subscription_canceled
            send_subscription_canceled(sub.user, plan_name)
        except Exception as exc:
            logger.warning('Falha ao enviar email de cancelamento: %s', exc)


def _handle_invoice_paid(invoice):
    sub = _find_subscription(invoice.get('subscription'), invoice.get('customer'))
    if sub:
        from .models import Subscription
        if sub.status != Subscription.STATUS_ACTIVE:
            sub.status = Subscription.STATUS_ACTIVE
            sub.save(update_fields=['status', 'updated_at'])


def _handle_invoice_failed(invoice):
    sub = _find_subscription(invoice.get('subscription'), invoice.get('customer'))
    if sub:
        from .models import Subscription
        sub.status = Subscription.STATUS_PAST_DUE
        sub.save(update_fields=['status', 'updated_at'])
        try:
            from .emails import send_payment_failed
            send_payment_failed(sub.user, sub.plan.name if sub.plan else 'Plano')
        except Exception as exc:
            logger.warning('Falha ao enviar email de falha de pagamento: %s', exc)
