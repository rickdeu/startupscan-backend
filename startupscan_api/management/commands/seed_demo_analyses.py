"""
Seeds the database with realistic PitchAnalysis records for demos and testing.

Runs each generated pitch through the real local ML pipeline (same code path
used by a live submission) so the resulting score, category breakdown and
report read exactly like a genuine analysis.

Usage:
    python manage.py seed_demo_analyses
    python manage.py seed_demo_analyses --count 150
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

STARTUP_TEMPLATES = [
    {
        "name": "AgroLink",
        "industry": "tech",
        "text": (
            "AgroLink connects smallholder farmers across Angola directly to urban buyers through a "
            "mobile marketplace, cutting out three layers of middlemen. Farmers list produce by photo and "
            "quantity, buyers place orders with mobile money, and our logistics partners handle last-mile "
            "delivery within 48 hours. In the last two quarters we onboarded over 600 farmers and 40 retail "
            "buyers, and repeat purchase rate sits above 60%. Our team combines agritech experience from "
            "Kenya with local distribution know-how, and we are raising a seed round to expand cold-chain "
            "storage into two more provinces."
        ),
        "revenue": (80_000, 420_000),
        "growth_rate": (15, 60),
        "profit_margin": (5, 22),
        "burn_rate": (4_000, 18_000),
    },
    {
        "name": "EduPro Angola",
        "industry": "education",
        "text": (
            "EduPro Angola is an online professional certification platform teaching in-demand digital "
            "skills to young adults in Portuguese, with bite-sized video lessons designed for low-bandwidth "
            "mobile connections. We partner with local employers to guarantee interviews for top graduates, "
            "which drives strong word-of-mouth growth. Since launch we have certified over 2,000 students "
            "and signed hiring partnerships with 12 companies in Luanda. Our founding team has backgrounds "
            "in EdTech product design and vocational training, and this round funds course catalogue "
            "expansion and a native mobile app."
        ),
        "revenue": (40_000, 260_000),
        "growth_rate": (20, 75),
        "profit_margin": (-5, 18),
        "burn_rate": (3_000, 14_000),
    },
    {
        "name": "MicroCred",
        "industry": "finance",
        "text": (
            "MicroCred provides short-term working capital loans to informal-sector small businesses using "
            "an alternative credit score built from mobile money transaction history rather than traditional "
            "collateral. Loans are disbursed within minutes through our app and repaid via automatic mobile "
            "money deduction. Default rates on our pilot cohort of 900 borrowers sit at 4.2%, well below "
            "regional microfinance benchmarks. The founding team includes former risk analysts from a "
            "regional commercial bank, and funds raised will scale the lending book and add a savings "
            "product."
        ),
        "revenue": (150_000, 900_000),
        "growth_rate": (25, 80),
        "profit_margin": (10, 30),
        "burn_rate": (8_000, 35_000),
    },
    {
        "name": "EntregaJa",
        "industry": "ecommerce",
        "text": (
            "EntregaJa is a last-mile delivery platform for e-commerce sellers in Luanda who currently rely "
            "on informal motorcycle couriers with no tracking or accountability. Our app dispatches vetted "
            "riders, gives sellers and customers real-time tracking, and settles cash-on-delivery payments "
            "automatically. We are processing over 1,800 deliveries per week across three neighborhoods "
            "with a 96% on-time rate. The team has prior experience scaling logistics operations in Nigeria, "
            "and this round funds rider fleet expansion and route optimization software."
        ),
        "revenue": (60_000, 380_000),
        "growth_rate": (18, 65),
        "profit_margin": (2, 16),
        "burn_rate": (5_000, 22_000),
    },
    {
        "name": "SafeSchool",
        "industry": "tech",
        "text": (
            "SafeSchool is a school-transport safety platform that equips minibus fleets with GPS trackers "
            "and gives parents a live app showing their child's pickup and drop-off status. Schools "
            "subscribe on a per-vehicle basis and we handle hardware installation and support. We currently "
            "cover 45 vehicles across 9 private schools with a 92% subscription renewal rate. Our founders "
            "previously built fleet-tracking software for a regional trucking company, and funding will "
            "accelerate sales into the public school segment."
        ),
        "revenue": (30_000, 180_000),
        "growth_rate": (12, 55),
        "profit_margin": (0, 20),
        "burn_rate": (3_500, 15_000),
    },
    {
        "name": "SaudeConecta",
        "industry": "health",
        "text": (
            "SaudeConecta is a telemedicine platform connecting patients in underserved provinces with "
            "licensed doctors in Luanda via video consultation, with a network of partner pharmacies for "
            "prescription fulfillment. Average consultation cost is 70% lower than an in-person specialist "
            "visit. In our first year we completed over 5,000 consultations and maintained a 4.7/5 patient "
            "satisfaction score. The founding team includes two practicing physicians and a health-tech "
            "product lead, and this round funds expansion into three additional provinces."
        ),
        "revenue": (70_000, 500_000),
        "growth_rate": (20, 70),
        "profit_margin": (5, 25),
        "burn_rate": (6_000, 28_000),
    },
    {
        "name": "ImobiFacil",
        "industry": "other",
        "text": (
            "ImobiFacil is a property listings and rental-management marketplace that lets landlords list "
            "verified properties and collect rent digitally, addressing the widespread problem of "
            "unverified listings and cash-only payments in the local rental market. We list over 1,200 "
            "properties across four cities and process rent for 300+ active tenancies each month. The team "
            "has backgrounds in proptech and payments, and funds raised will grow the verification team and "
            "add a tenant credit-history product."
        ),
        "revenue": (50_000, 300_000),
        "growth_rate": (10, 45),
        "profit_margin": (8, 28),
        "burn_rate": (4_000, 17_000),
    },
    {
        "name": "SolarKap",
        "industry": "other",
        "text": (
            "SolarKap sells and finances small solar home systems to off-grid households through a "
            "pay-as-you-go model billed via mobile money, replacing costly and unreliable kerosene and "
            "diesel generators. We have installed systems in over 3,400 households with a 91% on-time "
            "payment rate over 18 months. Our team combines solar hardware engineering with fintech "
            "collections experience, and this round funds inventory for the next 10,000-unit rollout."
        ),
        "revenue": (100_000, 650_000),
        "growth_rate": (22, 70),
        "profit_margin": (6, 24),
        "burn_rate": (7_000, 30_000),
    },
    {
        "name": "ContaCerta",
        "industry": "finance",
        "text": (
            "ContaCerta is cloud accounting and invoicing software built for small and medium businesses "
            "that currently manage finances on paper or spreadsheets, with built-in compliance for local "
            "tax filing requirements. We have 850 paying subscribers on monthly plans and a churn rate under "
            "3% per month. The founders previously built accounting tools for the Portuguese SMB market, "
            "and this round funds a mobile app and integrations with major local banks."
        ),
        "revenue": (90_000, 520_000),
        "growth_rate": (18, 58),
        "profit_margin": (15, 35),
        "burn_rate": (5_000, 20_000),
    },
    {
        "name": "TalentoUp",
        "industry": "tech",
        "text": (
            "TalentoUp is a recruitment marketplace matching skilled tradespeople — electricians, welders, "
            "plumbers — with short-term contract work, addressing chronic underemployment in the skilled "
            "trades. Workers build a verified profile with completed-job ratings, and employers post jobs "
            "with automatic candidate shortlists. We have placed over 1,100 workers with a 4.6/5 average "
            "employer rating. The team has staffing-industry and marketplace product experience, and funds "
            "raised will grow the employer sales team."
        ),
        "revenue": (45_000, 280_000),
        "growth_rate": (15, 62),
        "profit_margin": (4, 20),
        "burn_rate": (4_000, 16_000),
    },
]

INDUSTRY_EMAIL_DOMAINS = {
    "tech": "tech.ao",
    "health": "saude.ao",
    "finance": "fin.ao",
    "education": "edu.ao",
    "ecommerce": "shop.ao",
    "other": "startup.ao",
}


class Command(BaseCommand):
    help = "Seeds the database with realistic PitchAnalysis demo records, run through the real ML pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100, help="Number of analyses to generate (default: 100)")
        parser.add_argument(
            "--assign-existing-users",
            action="store_true",
            default=True,
            help="Randomly assign some analyses to existing entrepreneur users (default: True)",
        )

    def handle(self, *args, **options):
        count = options["count"]

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
            template = STARTUP_TEMPLATES[i % len(STARTUP_TEMPLATES)]
            variant = i // len(STARTUP_TEMPLATES)
            startup_name = template["name"] if variant == 0 else f"{template['name']} {variant + 1}"
            industry = template["industry"]

            revenue = round(random.uniform(*template["revenue"]), 2)
            growth_rate = round(random.uniform(*template["growth_rate"]), 2)
            profit_margin = round(random.uniform(*template["profit_margin"]), 2)
            burn_rate = round(random.uniform(*template["burn_rate"]), 2)

            traction_note = (
                f" As of this submission, monthly revenue stands at approximately {revenue:,.0f} AOA "
                f"with {growth_rate:.1f}% month-over-month growth."
            )
            text = template["text"] + traction_note

            pitch_data = {"text": text}
            financial_data = {
                "revenue": revenue,
                "growth_rate": growth_rate,
                "profit_margin": profit_margin,
            }

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
            report = generate_interpretable_report(prediction, metadata)
            report = ensure_report_dict(report, prediction)

            user = None
            if entrepreneur_users and random.random() < 0.4:
                user = random.choice(entrepreneur_users)

            domain = INDUSTRY_EMAIL_DOMAINS.get(industry, "startup.ao")
            contact_email = f"contact@{startup_name.lower().replace(' ', '')}.{domain}"

            days_ago = random.randint(0, 180)
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))

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
                confidence=round(random.uniform(68, 96), 1),
                report=report,
                metadata=metadata,
                status="completed",
                model_version=active_model_name,
                processing_time=round(random.uniform(2.5, 11.0), 2),
                submission_date=created_at.date(),
            )
            PitchAnalysis.objects.filter(pk=analysis.pk).update(
                created_at=created_at, updated_at=created_at,
            )

            created += 1
            if created % 10 == 0:
                self.stdout.write(f"  {created}/{count} generated...")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {created} demo PitchAnalysis records created."
        ))
