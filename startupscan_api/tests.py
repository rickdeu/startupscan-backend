from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    IdeaPitchSubmission,
    IdeaPublicFeedback,
    InvestorConnectionInterest,
    PitchAnalysis,
    UserProfile,
)


def make_pitch_analysis(**overrides):
    defaults = dict(
        text="We help startups get funded.",
        revenue=Decimal("1000000"),
        growth_rate=Decimal("50"),
        profit_margin=Decimal("20"),
    )
    defaults.update(overrides)
    return PitchAnalysis.objects.create(**defaults)


class UserProfileModelTests(TestCase):
    def test_default_role_is_general_public(self):
        user = User.objects.create_user(username="carol", password="pw")
        profile = UserProfile.objects.create(user=user)
        self.assertEqual(profile.role, UserProfile.ROLE_GENERAL_PUBLIC)

    def test_str_includes_username_and_role_label(self):
        user = User.objects.create_user(username="carol", password="pw")
        profile = UserProfile.objects.create(user=user, role=UserProfile.ROLE_INVESTOR)
        self.assertEqual(str(profile), "carol (Investor)")


class PitchAnalysisModelTests(TestCase):
    def test_save_defaults_submission_date_to_today(self):
        analysis = make_pitch_analysis()
        self.assertEqual(analysis.submission_date, date.today())

    def test_save_keeps_explicit_submission_date(self):
        chosen = date(2024, 1, 1)
        analysis = make_pitch_analysis(submission_date=chosen)
        self.assertEqual(analysis.submission_date, chosen)

    def test_is_completed_reflects_status(self):
        analysis = make_pitch_analysis(status="pending")
        self.assertFalse(analysis.is_completed)
        analysis.status = "completed"
        analysis.save()
        self.assertTrue(analysis.is_completed)

    def test_financial_health_combines_growth_and_margin(self):
        analysis = make_pitch_analysis(
            revenue=Decimal("1000000"), growth_rate=Decimal("50"), profit_margin=Decimal("20")
        )
        # (50*0.4 + 20*0.6) * 1_000_000 / 1_000_000 = 32
        self.assertEqual(analysis.financial_health, 32.0)

    def test_financial_health_none_when_growth_rate_is_zero(self):
        # growth_rate=0 is falsy, so the `all([...])` guard treats it as missing data.
        analysis = make_pitch_analysis(growth_rate=Decimal("0"))
        self.assertIsNone(analysis.financial_health)

    def test_get_file_links_empty_without_uploads(self):
        analysis = make_pitch_analysis()
        self.assertEqual(analysis.get_file_links(), {})

    def test_str_uses_startup_name_or_fallback(self):
        analysis = make_pitch_analysis(startup_name="Acme")
        self.assertIn("Acme", str(analysis))
        analysis_no_name = make_pitch_analysis(startup_name=None)
        self.assertIn(f"Analysis #{analysis_no_name.id}", str(analysis_no_name))


class IdeaPitchSubmissionModelTests(TestCase):
    def test_defaults_to_draft_status(self):
        submission = IdeaPitchSubmission.objects.create(
            startup_name="Acme",
            problem="No one can find parking",
            solution="An app",
            target_customer="Drivers",
            business_model="Freemium",
        )
        self.assertEqual(submission.status, "draft")

    def test_str_includes_startup_name_and_status(self):
        submission = IdeaPitchSubmission.objects.create(
            startup_name="Acme",
            problem="No one can find parking",
            solution="An app",
            target_customer="Drivers",
            business_model="Freemium",
        )
        self.assertEqual(str(submission), "Acme (Draft)")


class IdeaPublicFeedbackModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dave", password="pw")
        self.submission = IdeaPitchSubmission.objects.create(
            startup_name="Acme",
            problem="No one can find parking",
            solution="An app",
            target_customer="Drivers",
            business_model="Freemium",
        )

    def test_stars_out_of_range_fails_validation(self):
        feedback = IdeaPublicFeedback(submission=self.submission, user=self.user, stars=6)
        with self.assertRaises(ValidationError):
            feedback.full_clean()

    def test_duplicate_feedback_per_user_and_submission_is_rejected(self):
        IdeaPublicFeedback.objects.create(submission=self.submission, user=self.user, stars=5)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IdeaPublicFeedback.objects.create(
                    submission=self.submission, user=self.user, stars=3
                )


class InvestorConnectionInterestModelTests(TestCase):
    def setUp(self):
        self.investor = User.objects.create_user(username="investor1", password="pw")
        self.entrepreneur = User.objects.create_user(username="founder1", password="pw")
        self.analysis = make_pitch_analysis(startup_name="Acme", user=self.entrepreneur)

    def test_defaults_to_pending_status(self):
        interest = InvestorConnectionInterest.objects.create(
            analysis=self.analysis, investor=self.investor, entrepreneur=self.entrepreneur
        )
        self.assertEqual(interest.status, InvestorConnectionInterest.STATUS_PENDING)

    def test_duplicate_interest_per_investor_and_analysis_is_rejected(self):
        InvestorConnectionInterest.objects.create(
            analysis=self.analysis, investor=self.investor, entrepreneur=self.entrepreneur
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                InvestorConnectionInterest.objects.create(
                    analysis=self.analysis, investor=self.investor, entrepreneur=self.entrepreneur
                )
