from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from .models import MonthlyUsage, Subscription, SubscriptionPlan


class SubscriptionPlanModelTests(TestCase):
    def test_str_includes_name_price_and_interval(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, price_usd=Decimal("29.00")
        )
        self.assertEqual(str(plan), "Pro ($29.00/month)")

    def test_price_cents(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, price_usd=Decimal("29.99")
        )
        self.assertEqual(plan.price_cents, 2999)

    def test_price_eur_display_falls_back_to_conversion_when_not_set(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, price_usd=Decimal("100")
        )
        self.assertEqual(plan.price_eur_display, Decimal("92"))

    def test_price_eur_display_uses_explicit_value_when_set(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO,
            price_usd=Decimal("100"), price_eur=Decimal("85"),
        )
        self.assertEqual(plan.price_eur_display, Decimal("85"))

    def test_price_aoa_display_falls_back_to_conversion_when_not_set(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, price_usd=Decimal("100")
        )
        self.assertEqual(plan.price_aoa_display, Decimal("91200"))

    def test_has_feature(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, video_upload=True
        )
        self.assertTrue(plan.has_feature("video_upload"))
        self.assertFalse(plan.has_feature("gpt_analysis"))
        self.assertFalse(plan.has_feature("not_a_real_field"))

    def test_is_within_limit_unlimited_when_zero(self):
        plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, batch_max_rows=0
        )
        self.assertTrue(plan.is_within_limit("batch_max_rows", 1_000_000))

    def test_is_within_limit_respects_positive_limit(self):
        plan = SubscriptionPlan.objects.create(
            name="Basic", tier=SubscriptionPlan.TIER_BASIC, analyses_per_month=3
        )
        self.assertTrue(plan.is_within_limit("analyses_per_month", 2))
        self.assertFalse(plan.is_within_limit("analyses_per_month", 3))


class SubscriptionModelTests(TestCase):
    def setUp(self):
        # Creating a User fires subscriptions.signals.create_trial_subscription,
        # which auto-provisions a trial Subscription (OneToOneField to User).
        # Tests must reuse/overwrite that row rather than creating a second one.
        self.user = User.objects.create_user(username="alice", password="pw")
        self.plan = SubscriptionPlan.objects.create(
            name="Pro", tier=SubscriptionPlan.TIER_PRO, price_usd=Decimal("29")
        )

    def _set_subscription(self, **fields):
        sub, _ = Subscription.objects.update_or_create(user=self.user, defaults=fields)
        return sub

    def test_is_active_trialing_without_trial_end(self):
        sub = self._set_subscription(plan=self.plan, status=Subscription.STATUS_TRIALING, trial_end=None)
        self.assertTrue(sub.is_active)

    def test_is_active_trialing_with_future_trial_end(self):
        sub = self._set_subscription(
            plan=self.plan, status=Subscription.STATUS_TRIALING,
            trial_end=timezone.now() + timedelta(days=3),
        )
        self.assertTrue(sub.is_active)

    def test_is_active_trialing_with_past_trial_end(self):
        sub = self._set_subscription(
            plan=self.plan, status=Subscription.STATUS_TRIALING,
            trial_end=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(sub.is_active)

    def test_is_active_canceled(self):
        sub = self._set_subscription(plan=self.plan, status=Subscription.STATUS_CANCELED)
        self.assertFalse(sub.is_active)

    def test_trial_days_left_zero_when_not_trialing(self):
        sub = self._set_subscription(
            plan=self.plan, status=Subscription.STATUS_ACTIVE,
            trial_end=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(sub.trial_days_left, 0)

    def test_trial_days_left_counts_remaining_days(self):
        sub = self._set_subscription(
            plan=self.plan, status=Subscription.STATUS_TRIALING,
            trial_end=timezone.now() + timedelta(days=10, hours=1),
        )
        self.assertEqual(sub.trial_days_left, 10)

    def test_plan_tier_falls_back_to_trial_without_plan(self):
        sub = self._set_subscription(plan=None)
        self.assertEqual(sub.plan_tier, SubscriptionPlan.TIER_TRIAL)

    def test_plan_tier_matches_assigned_plan(self):
        sub = self._set_subscription(plan=self.plan)
        self.assertEqual(sub.plan_tier, SubscriptionPlan.TIER_PRO)


class MonthlyUsageModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="pw")

    def test_get_or_create_current_creates_row_for_this_month(self):
        usage = MonthlyUsage.get_or_create_current(self.user)
        now = timezone.now()
        self.assertEqual(usage.year, now.year)
        self.assertEqual(usage.month, now.month)
        self.assertEqual(usage.analyses_count, 0)

    def test_get_or_create_current_reuses_existing_row(self):
        first = MonthlyUsage.get_or_create_current(self.user)
        second = MonthlyUsage.get_or_create_current(self.user)
        self.assertEqual(first.pk, second.pk)

    def test_increment_persists_and_accumulates(self):
        MonthlyUsage.increment(self.user, "analyses_count")
        usage = MonthlyUsage.increment(self.user, "analyses_count")
        self.assertEqual(usage.analyses_count, 2)

    def test_unique_together_per_user_year_month(self):
        now = timezone.now()
        MonthlyUsage.objects.create(user=self.user, year=now.year, month=now.month)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MonthlyUsage.objects.create(user=self.user, year=now.year, month=now.month)
