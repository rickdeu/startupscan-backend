"""
Seeds the database with realistic IdeaPitchSubmission demo records for demos and testing.

Runs each idea through the real local pitch generator (same code path used by a live
"generate pitch" submission), so the resulting generated_pitch content reads exactly
like a genuine pitch generation.

Usage:
    python manage.py seed_demo_idea_pitches
    python manage.py seed_demo_idea_pitches --count 150
"""
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from startupscan_api.models import IdeaPitchSubmission
from startupscan_api.roles import ROLE_ENTREPRENEUR
from startupscan_api.services.pitch.generator import generate_pitch_from_idea

IDEA_TEMPLATES = [
    {
        "name": "FarmTrack",
        "one_liner": "Real-time crop-health monitoring for smallholder farmers using low-cost satellite imagery.",
        "problem": "Smallholder farmers have no affordable way to detect crop stress, pests, or irrigation problems before yield loss becomes visible to the naked eye.",
        "solution": "A subscription service that analyzes weekly satellite imagery of a farmer's registered plots and sends plain-language SMS alerts about stress zones, with recommended actions.",
        "target_customer": "Smallholder and mid-size commercial farmers across Southern Africa growing maize, soy, and coffee.",
        "market_size": "Over 4 million commercial farming households across the target region, with agritech penetration below 6%.",
        "business_model": "Flat monthly subscription per hectare monitored, billed via mobile money, with a free tier capped at 2 hectares.",
        "competitive_advantage": "Proprietary imagery-processing pipeline tuned for smallholder plot sizes, plus an SMS-first design that works without smartphones.",
        "traction": "120 pilot farmers across two provinces, 78% renewal after the first paid month.",
        "team": "Agronomist co-founder with 12 years of extension-service experience, plus a remote-sensing engineer.",
        "funding_goal": "$250,000 seed round",
        "use_of_funds": "Imagery licensing costs, SMS gateway scaling, and a three-person field agent team.",
        "call_to_action": "Looking for agritech-focused seed investors for a 20-minute intro call this month.",
    },
    {
        "name": "PayLoop",
        "one_liner": "Instant B2B invoice factoring for small suppliers waiting 60+ days to get paid.",
        "problem": "Small suppliers to large retailers routinely wait 60-90 days for invoice payment, starving them of working capital to fulfill the next order.",
        "solution": "A platform that verifies approved invoices directly with buyers and advances 85% of the invoice value within 24 hours, collecting the fee on settlement.",
        "target_customer": "Small and medium manufacturers and distributors supplying large retail chains.",
        "market_size": "Estimated $1.2B in annual unpaid supplier invoices sitting in the target retail supply chains.",
        "business_model": "Transaction fee of 2-4% per invoice advanced, scaling down with supplier volume.",
        "competitive_advantage": "Direct API integrations with three of the largest regional retailers for real-time invoice verification.",
        "traction": "$340,000 in invoices factored in the last quarter across 40 suppliers, 0% default rate.",
        "team": "Founders with prior careers in trade finance and supply-chain software.",
        "funding_goal": "$1,000,000 seed extension",
        "use_of_funds": "Expanding the lending facility and onboarding two more retail integration partners.",
        "call_to_action": "Raising a bridge to close our credit facility before the next fundraising cycle.",
    },
    {
        "name": "ShiftWise",
        "one_liner": "AI-powered shift scheduling for retail and hospitality teams that cuts no-shows in half.",
        "problem": "Hourly workers frequently miss shifts because managers build schedules manually with no visibility into worker availability or commute constraints.",
        "solution": "A scheduling app that lets workers set live availability, auto-fills shifts using a fairness-aware algorithm, and sends automated confirmation reminders.",
        "target_customer": "Retail chains and restaurant groups with 20 or more hourly staff per location.",
        "market_size": "Tens of thousands of multi-location retail and hospitality operators in the target markets.",
        "business_model": "Per-location monthly SaaS fee with tiered pricing based on headcount.",
        "competitive_advantage": "Fairness-aware scheduling engine that reduced no-shows by 48% in pilot locations, versus generic calendar tools.",
        "traction": "35 paying locations, average no-show rate dropped from 14% to 7% within two months of adoption.",
        "team": "Former operations lead at a national restaurant chain, plus a machine-learning engineer.",
        "funding_goal": "$500,000 pre-seed round",
        "use_of_funds": "Sales hires and building native integrations with point-of-sale systems.",
        "call_to_action": "Open to intro calls with investors focused on vertical SaaS for frontline workforces.",
    },
    {
        "name": "ClearRent",
        "one_liner": "Verified rental listings and digital rent collection for landlords tired of cash-only tenants.",
        "problem": "Renters and landlords both lose money and time to unverified listings, cash-only payments, and disputes with no paper trail.",
        "solution": "A marketplace where landlords list verified properties and collect rent digitally, with automatic receipts and a shared payment history both parties can trust.",
        "target_customer": "Independent landlords and small property managers in fast-growing urban markets.",
        "market_size": "Hundreds of thousands of rental units in the target metro areas, over 80% still managed informally.",
        "business_model": "A small percentage fee on each digital rent payment processed, plus a premium tier for property managers.",
        "competitive_advantage": "In-house verification team that physically confirms every new listing, eliminating the fraud that plagues open marketplaces.",
        "traction": "1,400 verified listings live, 320 active tenancies paying rent through the platform monthly.",
        "team": "Founders with backgrounds in proptech and consumer payments.",
        "funding_goal": "$750,000 seed round",
        "use_of_funds": "Growing the verification team and expanding to two additional cities.",
        "call_to_action": "Seeking proptech investors for our upcoming seed close.",
    },
    {
        "name": "NovaHealth",
        "one_liner": "On-demand nurse home visits booked in under five minutes through a mobile app.",
        "problem": "Patients recovering from surgery or managing chronic conditions often need routine nursing care but face long waits for in-clinic appointments or expensive private visits.",
        "solution": "An app that matches patients with vetted, licensed nurses for home visits, with transparent pricing and same-day availability in covered areas.",
        "target_customer": "Post-surgical and chronic-care patients, plus their families, in urban and peri-urban areas.",
        "market_size": "A large and growing home-healthcare segment driven by hospital discharge pressure and an aging population.",
        "business_model": "Per-visit fee with a percentage retained by the platform, plus a subscription plan for recurring care needs.",
        "competitive_advantage": "A rigorous nurse-vetting pipeline and real-time dispatch logic that keeps average response time under 90 minutes.",
        "traction": "5,200 completed visits in year one, 4.8/5 average patient rating.",
        "team": "Two practicing nurses and a product lead with prior health-tech experience.",
        "funding_goal": "$1,500,000 seed round",
        "use_of_funds": "Expanding the nurse network into three new districts and building insurer billing integrations.",
        "call_to_action": "Looking to connect with health-tech investors ahead of our next funding round.",
    },
    {
        "name": "RouteWise",
        "one_liner": "Route optimization software that cuts last-mile delivery costs by up to 30%.",
        "problem": "Small delivery fleets plan routes manually or with generic mapping tools, wasting fuel and driver hours on inefficient sequencing.",
        "solution": "A dispatch dashboard that ingests daily delivery addresses and outputs optimized, driver-ready routes in seconds, accounting for traffic and delivery windows.",
        "target_customer": "Regional courier companies and e-commerce sellers running their own delivery fleets.",
        "market_size": "A large and fragmented last-mile logistics market with most fleets still using manual or generic planning tools.",
        "business_model": "Per-vehicle monthly subscription with usage-based overage pricing for high-volume fleets.",
        "competitive_advantage": "A routing engine tuned specifically for motorcycle and light-vehicle couriers common in the target markets, unlike generic Western logistics tools.",
        "traction": "18 fleet customers managing over 200 vehicles, average reported fuel savings of 22%.",
        "team": "Founders with prior experience scaling logistics operations across multiple African markets.",
        "funding_goal": "$600,000 seed round",
        "use_of_funds": "Engineering headcount and expanding the traffic-data partnerships to new cities.",
        "call_to_action": "Raising our seed round now, happy to share the full data room on request.",
    },
    {
        "name": "SkillBridge",
        "one_liner": "A marketplace connecting skilled tradespeople with verified short-term contract work.",
        "problem": "Skilled tradespeople such as electricians and welders face chronic underemployment because they lack an efficient way to find short-term contract work matching their certifications.",
        "solution": "A marketplace where workers build a verified profile with completed-job ratings, and employers post jobs that get automatic candidate shortlists.",
        "target_customer": "Independent tradespeople and the small-to-mid-size contractors who hire them.",
        "market_size": "A large informal skilled-trades labor market with minimal digital intermediation today.",
        "business_model": "A placement fee charged to employers per successful hire, with free profiles for workers.",
        "competitive_advantage": "A verification process combining certification checks with completed-job ratings, building trust generic job boards lack.",
        "traction": "1,100 workers placed to date, 4.6/5 average employer rating.",
        "team": "Founders with staffing-industry and marketplace product backgrounds.",
        "funding_goal": "$400,000 seed round",
        "use_of_funds": "Growing the employer-facing sales team and expanding trade categories covered.",
        "call_to_action": "Open to meeting investors with marketplace or future-of-work experience.",
    },
    {
        "name": "BrightClass",
        "one_liner": "Bite-sized, mobile-first professional certification courses designed for low-bandwidth connections.",
        "problem": "Young adults seeking in-demand digital skills often can't access quality training because most e-learning platforms assume reliable broadband and desktop access.",
        "solution": "A mobile-first certification platform with short video lessons optimized for low-bandwidth connections, plus employer partnerships that guarantee interviews for top graduates.",
        "target_customer": "Young adults seeking entry-level digital-skills jobs in urban and peri-urban areas.",
        "market_size": "A large and growing pool of underemployed young adults with smartphone access but limited broadband.",
        "business_model": "Course fees paid up front or via installment plans, plus placement fees from hiring-partner employers.",
        "competitive_advantage": "A low-bandwidth-first product design and direct hiring pipelines that generic MOOCs don't offer.",
        "traction": "2,000+ students certified, hiring partnerships with a dozen employers.",
        "team": "Founders with backgrounds in EdTech product design and vocational training.",
        "funding_goal": "$350,000 seed round",
        "use_of_funds": "Expanding the course catalogue and building a native mobile app.",
        "call_to_action": "Fundraising now to close our seed round within the quarter.",
    },
]

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


def _weighted_choice(pairs):
    values, weights = zip(*pairs)
    return random.choices(values, weights=weights, k=1)[0]


class Command(BaseCommand):
    help = "Seeds the database with realistic IdeaPitchSubmission demo records, run through the real pitch generator."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100, help="Number of idea pitches to generate (default: 100)")

    def handle(self, *args, **options):
        count = options["count"]

        entrepreneur_users = list(
            User.objects.filter(profile__role=ROLE_ENTREPRENEUR)
        )

        created = 0
        failed = 0
        now = timezone.now()

        for i in range(count):
            template = IDEA_TEMPLATES[i % len(IDEA_TEMPLATES)]
            variant = i // len(IDEA_TEMPLATES)
            startup_name = template["name"] if variant == 0 else f"{template['name']} {variant + 1}"

            idea_data = {**template, "startup_name": startup_name}
            idea_data.pop("name", None)

            language = _weighted_choice(LANGUAGE_WEIGHTS)
            status = _weighted_choice(STATUS_CHOICES_WEIGHTED)

            user = None
            if entrepreneur_users and random.random() < 0.5:
                user = random.choice(entrepreneur_users)

            days_ago = random.randint(0, 365)
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))

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
                    generated_at = created_at + timedelta(minutes=random.randint(1, 30))

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
            if created % 10 == 0:
                self.stdout.write(f"  {created}/{count} generated...")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {created} demo IdeaPitchSubmission records created ({failed} generation failures fell back to draft)."
        ))
