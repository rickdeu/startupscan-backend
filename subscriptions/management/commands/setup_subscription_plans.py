"""
Creates or updates the initial subscription plans in the DB and syncs them with Stripe.

Usage:
    python manage.py setup_subscription_plans
    python manage.py setup_subscription_plans --sync-stripe
"""
import logging

from django.core.management.base import BaseCommand

from subscriptions.models import SubscriptionPlan
from subscriptions.stripe_sync import sync_plan_to_stripe

logger = logging.getLogger(__name__)

PLANS = [
    {
        'name': 'Trial',
        'tier': SubscriptionPlan.TIER_TRIAL,
        'interval': SubscriptionPlan.INTERVAL_ONCE,
        'price_usd': 0,
        'price_eur': 0,
        'price_aoa': 0,
        'trial_days': 7,
        'is_active': True,
        # Feature gates
        'analyses_per_month': 3,
        'videos_per_month': 0,
        'investor_interests_per_month': 0,
        'batch_max_rows': 0,
        'gpt_analysis': False,
        'audio_upload': False,
        'video_upload': False,
        'youtube_url': False,
        'financial_data': False,
        'pdf_report': False,
        'pdf_investor': False,
        'pitch_template_choice': False,
        'pitch_gpt': False,
        'pitch_pdf': False,
        'batch_analysis': False,
        'investor_dashboard': False,
        'video_generation': False,
    },
    {
        'name': 'Basic Monthly',
        'tier': SubscriptionPlan.TIER_BASIC,
        'interval': SubscriptionPlan.INTERVAL_MONTH,
        'price_usd': 50,
        'price_eur': 46,
        'price_aoa': 45600,
        'trial_days': 0,
        'is_active': True,
        'analyses_per_month': 15,
        'videos_per_month': 0,
        'investor_interests_per_month': 5,
        'batch_max_rows': 0,
        'gpt_analysis': False,
        'audio_upload': False,
        'video_upload': False,
        'youtube_url': False,
        'financial_data': True,
        'pdf_report': True,
        'pdf_investor': False,
        'pitch_template_choice': False,
        'pitch_gpt': False,
        'pitch_pdf': True,
        'batch_analysis': False,
        'investor_dashboard': True,
        'video_generation': False,
    },
    {
        'name': 'Basic Yearly',
        'tier': SubscriptionPlan.TIER_BASIC,
        'interval': SubscriptionPlan.INTERVAL_YEAR,
        'price_usd': 400,
        'price_eur': 368,
        'price_aoa': 364800,
        'trial_days': 0,
        'is_active': True,
        'analyses_per_month': 15,
        'videos_per_month': 0,
        'investor_interests_per_month': 5,
        'batch_max_rows': 0,
        'gpt_analysis': False,
        'audio_upload': False,
        'video_upload': False,
        'youtube_url': False,
        'financial_data': True,
        'pdf_report': True,
        'pdf_investor': False,
        'pitch_template_choice': False,
        'pitch_gpt': False,
        'pitch_pdf': True,
        'batch_analysis': False,
        'investor_dashboard': True,
        'video_generation': False,
    },
    {
        'name': 'Pro Monthly',
        'tier': SubscriptionPlan.TIER_PRO,
        'interval': SubscriptionPlan.INTERVAL_MONTH,
        'price_usd': 150,
        'price_eur': 138,
        'price_aoa': 136800,
        'trial_days': 0,
        'is_active': True,
        'analyses_per_month': 0,
        'videos_per_month': 3,
        'investor_interests_per_month': 0,
        'batch_max_rows': 200,
        'gpt_analysis': True,
        'audio_upload': True,
        'video_upload': True,
        'youtube_url': True,
        'financial_data': True,
        'pdf_report': True,
        'pdf_investor': True,
        'pitch_template_choice': True,
        'pitch_gpt': True,
        'pitch_pdf': True,
        'batch_analysis': True,
        'investor_dashboard': True,
        'video_generation': True,
        'business_model_canvas': True,
    },
    {
        'name': 'Pro Yearly',
        'tier': SubscriptionPlan.TIER_PRO,
        'interval': SubscriptionPlan.INTERVAL_YEAR,
        'price_usd': 1200,
        'price_eur': 1104,
        'price_aoa': 1094400,
        'trial_days': 0,
        'is_active': True,
        'analyses_per_month': 0,
        'videos_per_month': 3,
        'investor_interests_per_month': 0,
        'batch_max_rows': 200,
        'gpt_analysis': True,
        'audio_upload': True,
        'video_upload': True,
        'youtube_url': True,
        'financial_data': True,
        'pdf_report': True,
        'pdf_investor': True,
        'pitch_template_choice': True,
        'pitch_gpt': True,
        'pitch_pdf': True,
        'batch_analysis': True,
        'investor_dashboard': True,
        'video_generation': True,
        'business_model_canvas': True,
    },
]


class Command(BaseCommand):
    help = 'Creates or updates the initial subscription plans and syncs them with Stripe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-stripe',
            action='store_true',
            default=True,
            help='Sync paid plans with Stripe (default: True)',
        )
        parser.add_argument(
            '--no-sync-stripe',
            action='store_false',
            dest='sync_stripe',
        )

    def handle(self, *args, **options):
        sync = options['sync_stripe']
        created_count = 0
        updated_count = 0

        for plan_data in PLANS:
            lookup = {'tier': plan_data['tier'], 'interval': plan_data['interval']}
            plan, created = SubscriptionPlan.objects.update_or_create(
                **lookup,
                defaults=plan_data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {plan.name}'))
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {plan.name}')

            if sync and plan.price_usd > 0:
                ok = sync_plan_to_stripe(plan)
                status = 'OK' if ok else 'FAILED (check STRIPE_SECRET_KEY)'
                self.stdout.write(f'    Stripe sync: {status}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {created_count} created, {updated_count} updated.'
        ))
