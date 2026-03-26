from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from startupscan_api.models import PaymentTransaction, SubscriptionPlan, SubscriptionPlanPrice, UserSubscription
from startupscan_api.modules.subscriptions.access import is_subscription_allowed_for_route
from startupscan_api.modules.payments.service import record_payment_from_invoice_event, sync_subscription_from_stripe_data
from startupscan_api.roles import ROLE_CHOICES_PUBLIC_REGISTRATION
from startupscan_api.roles import get_or_create_profile_for_user
from startupscan_api.modules.subscriptions.service import ensure_trial_for_user


class SubscriptionModuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        profile = get_or_create_profile_for_user(self.user)
        if profile is not None:
            profile.role = "empreendedor"
            profile.save(update_fields=["role", "updated_at"])
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.client.logout()
        self.client.login(username="alice", password="password123")
        self.basic_plan = SubscriptionPlan.objects.create(code="basic", name="Basic", is_active=True, display_order=1)
        self.pro_plan = SubscriptionPlan.objects.create(code="pro", name="Pro", is_active=True, display_order=2)
        SubscriptionPlanPrice.objects.create(
            plan=self.basic_plan,
            interval="monthly",
            amount_cents=2900,
            currency="usd",
            is_active=True,
            stripe_price_id="price_basic_monthly",
        )
        SubscriptionPlanPrice.objects.create(
            plan=self.basic_plan,
            interval="annual",
            amount_cents=29000,
            currency="usd",
            is_active=True,
            stripe_price_id="price_basic_annual",
        )
        SubscriptionPlanPrice.objects.create(
            plan=self.pro_plan,
            interval="monthly",
            amount_cents=7900,
            currency="usd",
            is_active=True,
            stripe_price_id="price_pro_monthly",
        )
        SubscriptionPlanPrice.objects.create(
            plan=self.pro_plan,
            interval="annual",
            amount_cents=79000,
            currency="usd",
            is_active=True,
            stripe_price_id="price_pro_annual",
        )

    def test_ensure_trial_for_user_creates_14_day_trial_with_full_access(self):
        subscription = ensure_trial_for_user(self.user)
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.status, UserSubscription.STATUS_TRIAL)
        self.assertTrue(subscription.has_full_access)
        self.assertIsNotNone(subscription.trial_started_at)
        self.assertIsNotNone(subscription.trial_ends_at)

        duration = subscription.trial_ends_at - subscription.trial_started_at
        self.assertGreaterEqual(duration, timedelta(days=13, hours=23))
        self.assertLessEqual(duration, timedelta(days=14, minutes=1))

    def test_subscription_me_endpoint_auto_starts_trial(self):
        response = self.client.get("/subscriptions/me/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("subscription", data)
        self.assertEqual(data["subscription"]["status"], UserSubscription.STATUS_TRIAL)
        self.assertTrue(data["subscription"]["has_full_access"])

    def test_sync_subscription_from_stripe_data_updates_local_subscription(self):
        subscription = ensure_trial_for_user(self.user)
        now_epoch = int(timezone.now().timestamp())
        stripe_payload = {
            "id": "sub_123",
            "customer": "cus_abc",
            "status": "active",
            "current_period_start": now_epoch,
            "current_period_end": now_epoch + 3600,
            "trial_start": now_epoch - 60,
            "trial_end": now_epoch + 600,
            "cancel_at_period_end": False,
            "metadata": {
                "user_id": str(self.user.id),
                "plan": "pro",
                "interval": "annual",
            },
        }

        synced = sync_subscription_from_stripe_data(stripe_payload)
        self.assertIsNotNone(synced)
        self.assertEqual(synced.id, subscription.id)
        self.assertEqual(synced.status, UserSubscription.STATUS_ACTIVE)
        self.assertEqual(synced.plan, "pro")
        self.assertEqual(synced.interval, "annual")
        self.assertEqual(synced.stripe_subscription_id, "sub_123")
        self.assertEqual(synced.stripe_customer_id, "cus_abc")

    def test_record_payment_from_invoice_event_creates_transaction(self):
        subscription = ensure_trial_for_user(self.user)
        subscription.stripe_subscription_id = "sub_invoice_1"
        subscription.save(update_fields=["stripe_subscription_id", "updated_at"])

        invoice_payload = {
            "id": "in_001",
            "subscription": "sub_invoice_1",
            "amount_paid": 7900,
            "amount_due": 7900,
            "currency": "usd",
            "status": "paid",
            "hosted_invoice_url": "https://example.com/invoice/in_001",
            "payment_intent": "pi_001",
            "status_transitions": {"paid_at": int(timezone.now().timestamp())},
        }

        transaction = record_payment_from_invoice_event(invoice_payload)
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.subscription_id, subscription.id)
        self.assertEqual(transaction.amount_cents, 7900)
        self.assertEqual(transaction.status, "paid")
        self.assertEqual(transaction.stripe_invoice_id, "in_001")
        self.assertEqual(transaction.stripe_payment_intent_id, "pi_001")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_basic_paid_subscription_blocks_premium_routes(self):
        subscription = ensure_trial_for_user(self.user)
        subscription.status = UserSubscription.STATUS_ACTIVE
        subscription.plan = "basic"
        subscription.interval = "monthly"
        subscription.current_period_end = timezone.now() + timedelta(days=30)
        subscription.save(
            update_fields=[
                "status",
                "plan",
                "interval",
                "current_period_end",
                "updated_at",
            ]
        )

        investor_response = self.client.get("/investors/")
        self.assertEqual(investor_response.status_code, 302)
        self.assertIn("/", investor_response.url)

        models_response = self.client.get("/models/")
        self.assertEqual(models_response.status_code, 302)

    def test_basic_paid_subscription_allows_core_routes(self):
        subscription = ensure_trial_for_user(self.user)
        subscription.status = UserSubscription.STATUS_ACTIVE
        subscription.plan = "basic"
        subscription.interval = "monthly"
        subscription.current_period_end = timezone.now() + timedelta(days=30)
        subscription.save(
            update_fields=[
                "status",
                "plan",
                "interval",
                "current_period_end",
                "updated_at",
            ]
        )

        profile_response = self.client.get("/profile/")
        self.assertEqual(profile_response.status_code, 200)

        pitch_response = self.client.get("/analyze/form/")
        self.assertEqual(pitch_response.status_code, 200)

    def test_route_access_helper_allows_non_mapped_routes(self):
        self.assertTrue(is_subscription_allowed_for_route("some_unknown_route", {"can_dashboard": False}))

    def test_public_landing_is_accessible_without_auth(self):
        anonymous = APIClient()
        response = anonymous.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "StartupScan")

    def test_register_role_choices_are_limited_to_public_entrepreneur_investor(self):
        role_codes = {code for code, _ in ROLE_CHOICES_PUBLIC_REGISTRATION}
        self.assertEqual(role_codes, {"publico_geral", "empreendedor", "investidor"})

    def test_sync_subscription_uses_db_catalog_by_stripe_price_id(self):
        subscription = ensure_trial_for_user(self.user)
        payload = {
            "id": "sub_sync_price",
            "customer": "cus_xyz",
            "status": "active",
            "current_period_start": int(timezone.now().timestamp()),
            "current_period_end": int((timezone.now() + timedelta(days=30)).timestamp()),
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_pro_annual",
                            "unit_amount": 79000,
                            "currency": "usd",
                            "active": True,
                            "recurring": {"interval": "year"},
                            "product": {
                                "id": "prod_pro",
                                "name": "Pro",
                                "metadata": {"plan_code": "pro"},
                            },
                        }
                    }
                ]
            },
            "metadata": {"user_id": str(self.user.id)},
        }
        synced = sync_subscription_from_stripe_data(payload)
        self.assertIsNotNone(synced)
        assert synced is not None
        self.assertEqual(synced.id, subscription.id)
        self.assertEqual(synced.plan, "pro")
        self.assertEqual(synced.interval, "annual")
