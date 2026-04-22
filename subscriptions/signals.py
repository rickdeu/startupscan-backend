from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone


@receiver(post_save, sender=User)
def create_trial_subscription(sender, instance, created, **kwargs):
    if not created:
        return

    from .models import Subscription, SubscriptionPlan

    if hasattr(instance, 'subscription'):
        return

    try:
        if Subscription.objects.filter(user=instance).exists():
            return

        trial_plan = SubscriptionPlan.objects.filter(
            tier=SubscriptionPlan.TIER_TRIAL, is_active=True,
        ).first()

        trial_days = trial_plan.trial_days if trial_plan else 7
        trial_end = timezone.now() + timezone.timedelta(days=trial_days)

        Subscription.objects.create(
            user=instance,
            plan=trial_plan,
            status=Subscription.STATUS_TRIALING,
            trial_end=trial_end,
        )

        if instance.email:
            try:
                from .emails import send_trial_started
                send_trial_started(instance, trial_end)
            except Exception as exc_email:
                import logging
                logging.getLogger(__name__).warning('Falha ao enviar email trial: %s', exc_email)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            'Falha ao criar subscrição trial para user %s: %s', instance.pk, exc,
        )
