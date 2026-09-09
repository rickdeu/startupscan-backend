"""
Seeds the database with realistic IdeaPitchSubmission demo records for demos and testing.

Runs each idea through the real local pitch generator (same code path used by a live
"generate pitch" submission), so the resulting generated_pitch content reads exactly
like a genuine pitch generation. Ideas are combined procedurally from independent
problem/solution/target/traction pools (see _demo_idea_bank.py) so large batches read
as different startups rather than a handful of templates repeated with a number
appended.

Run in batches (e.g. --count 500 several times) rather than one huge --count to keep
peak memory bounded — each invocation is a fresh process.

Usage:
    python manage.py seed_demo_idea_pitches
    python manage.py seed_demo_idea_pitches --count 500
"""
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from startupscan_api.models import IdeaPitchSubmission
from startupscan_api.roles import ROLE_ENTREPRENEUR
from startupscan_api.services.pitch.generator import generate_pitch_from_idea

from ._demo_idea_bank import (
    VERTICALS,
    build_call_to_action,
    build_market_size,
    build_one_liner,
    build_use_of_funds,
    generate_idea,
)

LANGUAGE_WEIGHTS = [
    ("en", 45),
    ("pt", 30),
    ("es", 8),
    ("de", 7),
    ("ru", 4),
    ("zh-hans", 3),
    ("umb", 3),
]

STATUS_CHOICES_WEIGHTED = [
    ("generated", 80),
    ("draft", 20),
]


def _weighted_choice(rng, pairs):
    values, weights = zip(*pairs)
    return rng.choices(values, weights=weights, k=1)[0]


class Command(BaseCommand):
    help = "Seeds the database with realistic IdeaPitchSubmission demo records, run through the real pitch generator."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100, help="Number of idea pitches to generate (default: 100)")
        parser.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducibility")

    def handle(self, *args, **options):
        count = options["count"]
        rng = random.Random(options.get("seed"))

        entrepreneur_users = list(
            User.objects.filter(profile__role=ROLE_ENTREPRENEUR)
        )

        created = 0
        failed = 0
        now = timezone.now()

        for i in range(count):
            vertical = VERTICALS[rng.randrange(len(VERTICALS))]
            picked = generate_idea(vertical, rng)
            startup_name = picked["startup_name"]

            idea_data = {
                "startup_name": startup_name,
                "one_liner": build_one_liner(picked),
                "problem": picked["problem"],
                "solution": picked["solution"],
                "target_customer": picked["target_customer"],
                "market_size": build_market_size(picked),
                "business_model": picked["business_model"],
                "competitive_advantage": picked["competitive_advantage"],
                "traction": picked["traction"].capitalize() + ".",
                "team": picked["team"].capitalize() + ".",
                "funding_goal": picked["funding_goal"],
                "use_of_funds": build_use_of_funds(picked),
                "call_to_action": build_call_to_action(picked),
            }

            language = _weighted_choice(rng, LANGUAGE_WEIGHTS)
            status = _weighted_choice(rng, STATUS_CHOICES_WEIGHTED)

            user = None
            if entrepreneur_users and rng.random() < 0.5:
                user = rng.choice(entrepreneur_users)

            days_ago = rng.randint(0, 365)
            created_at = now - timedelta(days=days_ago, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))

            generated_pitch = {}
            generated_at = None
            if status == "generated":
                try:
                    generated_pitch = generate_pitch_from_idea(idea_data, model_source="local", language=language)
                except Exception as exc:
                    failed += 1
                    self.stderr.write(self.style.WARNING(f"  generation failed for {startup_name} ({language}): {exc}"))
                    generated_pitch = {}
                    status = "draft"
                else:
                    generated_at = created_at + timedelta(minutes=rng.randint(1, 30))

            submission = IdeaPitchSubmission.objects.create(
                user=user,
                startup_name=startup_name,
                one_liner=idea_data["one_liner"],
                problem=idea_data["problem"],
                solution=idea_data["solution"],
                target_customer=idea_data["target_customer"],
                market_size=idea_data["market_size"],
                business_model=idea_data["business_model"],
                competitive_advantage=idea_data["competitive_advantage"],
                traction=idea_data["traction"],
                team=idea_data["team"],
                funding_goal=idea_data["funding_goal"],
                use_of_funds=idea_data["use_of_funds"],
                call_to_action=idea_data["call_to_action"],
                model_source="local",
                status=status,
                generated_pitch=generated_pitch,
                generated_at=generated_at,
            )
            IdeaPitchSubmission.objects.filter(pk=submission.pk).update(
                created_at=created_at, updated_at=generated_at or created_at,
            )

            created += 1
            if created % 25 == 0:
                self.stdout.write(f"  {created}/{count} generated...")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {created} demo IdeaPitchSubmission records created ({failed} generation failures fell back to draft)."
        ))
