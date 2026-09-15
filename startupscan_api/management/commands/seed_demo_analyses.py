"""
Seeds the database with realistic PitchAnalysis records for demos and testing.

Runs each generated pitch through the real local ML pipeline (same code path
used by a live submission) so the resulting score, category breakdown and
report read exactly like a genuine analysis. Ideas are combined procedurally
from independent problem/solution/target/traction pools (see
_demo_idea_bank.py) so large batches read as different startups rather than
the same handful of paragraphs repeated with a number appended. Reports are
generated across the platform's supported UI languages so demo data also
exercises multi-language rendering.

Run in batches (e.g. --count 500 several times) rather than one huge --count
to keep peak memory bounded — each invocation is a fresh process.

Usage:
    python manage.py seed_demo_analyses
    python manage.py seed_demo_analyses --count 500
"""
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from startupscan_api.modeling import ensure_report_dict
from startupscan_api.models import PitchAnalysis
from startupscan_api.roles import ROLE_ENTREPRENEUR
from startupscan_api.services.model_registry import get_active_model_name
from startupscan_api.services.model_training import ensure_model_exists, predict_pitch_score
from startupscan_api.utils import generate_interpretable_report, prepare_features

from ._demo_idea_bank import VERTICALS, build_pitch_paragraph, generate_idea

LANGUAGE_WEIGHTS = [
    ("en", 45),
    ("pt", 30),
    ("es", 8),
    ("de", 7),
    ("ru", 4),
    ("zh-hans", 3),
    ("umb", 3),
]


def _weighted_choice(rng, pairs):
    values, weights = zip(*pairs)
    return rng.choices(values, weights=weights, k=1)[0]


class Command(BaseCommand):
    help = "Seeds the database with realistic PitchAnalysis demo records, run through the real ML pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100, help="Number of analyses to generate (default: 100)")
        parser.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducibility")

    def handle(self, *args, **options):
        count = options["count"]
        rng = random.Random(options.get("seed"))

        model = ensure_model_exists()
        if model is None:
            self.stderr.write(self.style.ERROR("Local model unavailable — cannot seed demo analyses."))
            return

        active_model_name = get_active_model_name() or "pitch_model"

        entrepreneur_users = list(
            User.objects.filter(profile__role=ROLE_ENTREPRENEUR)
        )

        created = 0
        now = timezone.now()

        for i in range(count):
            vertical = VERTICALS[rng.randrange(len(VERTICALS))]
            idea = generate_idea(vertical, rng)
            startup_name = idea["startup_name"]
            industry = idea["industry"]

            revenue = round(rng.uniform(*idea["revenue_range"]), 2)
            growth_rate = round(rng.uniform(*idea["growth_range"]), 2)
            profit_margin = round(rng.uniform(*idea["margin_range"]), 2)
            burn_rate = round(rng.uniform(*idea["burn_range"]), 2)

            text = build_pitch_paragraph(idea)

            pitch_data = {"text": text}
            financial_data = {
                "revenue": revenue,
                "growth_rate": growth_rate,
                "profit_margin": profit_margin,
            }

            language = _weighted_choice(rng, LANGUAGE_WEIGHTS)

            features, metadata = prepare_features(pitch_data, financial_data)
            metadata["analysis_engine_requested"] = "local"
            metadata["startup_name"] = startup_name
            metadata["industry"] = industry
            metadata["analysis_engine_used"] = "local"

            prediction = predict_pitch_score(
                model=model, pitch_data=pitch_data,
                financial_data=financial_data, precomputed_features=features,
            )
            prediction = max(0.0, min(10.0, float(prediction)))
            report = generate_interpretable_report(prediction, metadata, language=language)
            report = ensure_report_dict(report, prediction)

            user = None
            if entrepreneur_users and rng.random() < 0.4:
                user = rng.choice(entrepreneur_users)

            slug = startup_name.lower().replace(" ", "")
            contact_email = f"contact@{slug}.{idea['email_domain']}"

            days_ago = rng.randint(0, 365)
            created_at = now - timedelta(days=days_ago, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))

            analysis = PitchAnalysis.objects.create(
                user=user,
                startup_name=startup_name,
                industry=industry,
                contact_email=contact_email,
                text=text,
                revenue=revenue,
                growth_rate=growth_rate,
                profit_margin=profit_margin,
                burn_rate=burn_rate,
                success_score=prediction,
                confidence=round(rng.uniform(68, 96), 1),
                report=report,
                metadata=metadata,
                status="completed",
                model_version=active_model_name,
                processing_time=round(rng.uniform(2.5, 11.0), 2),
                submission_date=created_at.date(),
            )
            PitchAnalysis.objects.filter(pk=analysis.pk).update(
                created_at=created_at, updated_at=created_at,
            )

            created += 1
            if created % 25 == 0:
                self.stdout.write(f"  {created}/{count} generated...")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {created} demo PitchAnalysis records created."
        ))
