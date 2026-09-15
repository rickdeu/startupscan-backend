"""
Shared building blocks for demo-data seed commands (not a Django management command
itself — the leading underscore keeps `manage.py` from registering it as one).

Rather than a fixed list of hand-written pitches (which reads as repetitive once
cycled hundreds of times), this module combines independent pools of problem /
solution / target-customer / differentiator / traction / business-model / team /
funding phrasings per vertical. Each generated idea samples one option from each
pool, so the combinatorial space per vertical is in the tens of thousands —
enough that thousands of generated demo records read as genuinely different
ideas instead of the same paragraph with a number appended.
"""
import random

VERTICALS = [
    {
        "key": "fintech_lending",
        "industry": "finance",
        "email_domain": "fin.ao",
        "name_prefixes": ["Kreda", "Fundi", "Capita", "Creditum", "PesaFlow", "LoanBridge", "Finabora"],
        "name_suffixes": ["", "Pay", "Credit", "Capital", "Finance", "Money"],
        "problems": [
            "informal-sector small businesses cannot access working capital because they lack the collateral or credit history traditional banks require",
            "short-term loan applications routinely take weeks to process, forcing small merchants to turn to predatory informal lenders",
            "millions of creditworthy small business owners are invisible to banks because their transaction history lives only in cash and mobile money logs",
            "existing microfinance products charge fees so high that repayment traps borrowers in a cycle of debt instead of growth",
        ],
        "solutions": [
            "an alternative credit-scoring engine built from mobile money transaction history that approves and disburses loans within minutes",
            "a lending platform that underwrites borrowers using real-time cash-flow data instead of collateral, with automatic mobile-money repayment",
            "a digital lending app that scores creditworthiness from utility and mobile-money payment patterns and disburses same-day",
            "a working-capital line that adjusts in real time to a merchant's sales volume, repaid automatically as revenue comes in",
        ],
        "targets": [
            "informal-sector micro and small businesses",
            "street vendors and small retail shop owners",
            "small manufacturers and service providers without formal credit history",
        ],
        "differentiators": [
            "a proprietary risk model trained on regional mobile-money data that traditional banks don't have access to",
            "an underwriting team with prior careers in regional retail-bank risk management",
            "disbursement times measured in minutes rather than the weeks a bank branch requires",
        ],
        "tractions": [
            "a pilot cohort of {n} borrowers with a default rate under 5%, well below regional microfinance benchmarks",
            "over {n} loans disbursed in the last two quarters with a 94% on-time repayment rate",
            "{n} active borrowers and a repeat-loan rate above 60%, signalling strong trust in the product",
        ],
        "business_models": [
            "an origination fee on each loan disbursed, plus interest spread on the outstanding book",
            "a flat processing fee per loan plus a small monthly account fee for a linked savings product",
            "interest income on the lending book, with a data-licensing revenue stream planned for year two",
        ],
        "teams": [
            "founders with prior careers as risk analysts at a regional commercial bank",
            "a team combining fintech product experience with a former microfinance branch manager",
        ],
        "fundings": ["$150,000 seed round", "$400,000 seed round", "$900,000 Series A"],
        "revenue_range": (100_000, 900_000),
        "growth_range": (20, 80),
        "margin_range": (8, 30),
        "burn_range": (6_000, 32_000),
    },
    {
        "key": "healthtech_telemedicine",
        "industry": "health",
        "email_domain": "saude.ao",
        "name_prefixes": ["SaudeConecta", "MediLink", "DocProximo", "CareBridge", "VitaConnect", "PulseCare"],
        "name_suffixes": ["", "Health", "Med", "Care", "Vita"],
        "problems": [
            "patients in underserved provinces have no reliable way to reach a licensed specialist without a full-day trip to the capital",
            "post-surgical patients often skip essential follow-up care because in-person appointments are expensive and hard to schedule",
            "rural clinics are chronically understaffed, leaving patients waiting weeks for basic consultations",
            "chronic-condition patients struggle to maintain consistent care because the closest specialist is hours away",
        ],
        "solutions": [
            "a telemedicine platform connecting patients with licensed doctors over video, with partner pharmacies handling prescription fulfillment",
            "an on-demand home-visit service that dispatches vetted nurses within a same-day window",
            "a remote-monitoring app that lets chronic-care patients check in with a care team without leaving home",
            "a video-consultation network paired with a triage chatbot that routes patients to the right specialist immediately",
        ],
        "targets": [
            "patients in underserved and rural provinces",
            "post-surgical and chronic-care patients recovering at home",
            "working professionals who can't take a full day off for an in-person visit",
        ],
        "differentiators": [
            "a vetting pipeline that only admits licensed, background-checked practitioners",
            "a partner-pharmacy network that closes the loop from diagnosis to medication in one flow",
            "average response times under 90 minutes, far below the regional home-care norm",
        ],
        "tractions": [
            "over {n} consultations completed in the first year with a 4.7/5 patient satisfaction score",
            "{n} active patients on recurring care plans and a 90% follow-up completion rate",
            "a network of {n} partner clinics and a 40% reduction in average time-to-consultation",
        ],
        "business_models": [
            "a per-consultation fee split with partner doctors, plus a premium subscription for unlimited chat triage",
            "a subscription plan for recurring care, billed monthly, with pay-per-visit for occasional users",
            "a per-visit fee with a percentage retained by the platform and the rest paid to the care provider",
        ],
        "teams": [
            "two practicing physicians and a product lead with prior health-tech experience",
            "a founding team combining clinical nursing experience with mobile-health engineering",
        ],
        "fundings": ["$300,000 seed round", "$750,000 seed round", "$1,500,000 Series A"],
        "revenue_range": (70_000, 600_000),
        "growth_range": (18, 70),
        "margin_range": (3, 25),
        "burn_range": (6_000, 30_000),
    },
    {
        "key": "edtech_certification",
        "industry": "education",
        "email_domain": "edu.ao",
        "name_prefixes": ["EduPro", "SkillNova", "BrightClass", "CertaAgora", "LearnBridge", "ProSkill"],
        "name_suffixes": ["", "Academy", "Skills", "Lab", "Learn"],
        "problems": [
            "young adults seeking digital-skills jobs can't access quality training because most courses assume broadband and desktop access they don't have",
            "vocational graduates struggle to convert certificates into job interviews because employers don't trust unverified course completions",
            "working adults can't fit multi-hour lecture-based courses into their schedules and drop out before certifying",
            "employers spend weeks screening candidates for basic digital skills that a short certification could verify instantly",
        ],
        "solutions": [
            "a mobile-first certification platform with short, low-bandwidth video lessons and employer-guaranteed interviews for top graduates",
            "a bite-sized skills curriculum with weekly live mentor sessions designed around a full-time work schedule",
            "a project-based certification track where employers help design the curriculum and pre-commit to interviewing graduates",
            "a skills-verification exam employers can trust, paired with a talent marketplace for certified graduates",
        ],
        "targets": [
            "young adults seeking entry-level digital-skills jobs",
            "working adults looking to reskill without quitting their job",
            "vocational-school graduates entering the job market",
        ],
        "differentiators": [
            "a low-bandwidth-first product design built for markets where most learners are smartphone-only",
            "direct hiring pipelines with employer partners that generic MOOCs don't offer",
            "a completion rate more than double the industry average for mobile-first online courses",
        ],
        "tractions": [
            "over {n} students certified and hiring partnerships with a dozen employers",
            "{n} active learners with a 70% course-completion rate, well above the sector norm",
            "{n} graduates placed into jobs within three months of certifying",
        ],
        "business_models": [
            "course fees paid up front or via installment plans, plus placement fees from hiring-partner employers",
            "a monthly subscription for the full course catalogue, plus one-time certification exam fees",
            "employer-sponsored cohorts where companies pay per trained employee",
        ],
        "teams": [
            "founders with backgrounds in EdTech product design and vocational training",
            "a team combining curriculum design experience with a former corporate recruiter",
        ],
        "fundings": ["$120,000 pre-seed round", "$350,000 seed round", "$800,000 seed round"],
        "revenue_range": (35_000, 300_000),
        "growth_range": (20, 75),
        "margin_range": (-5, 20),
        "burn_range": (3_000, 15_000),
    },
    {
        "key": "agritech",
        "industry": "tech",
        "email_domain": "tech.ao",
        "name_prefixes": ["AgroLink", "FarmTrack", "CampoDigital", "HarvestIQ", "AgroPulse", "TerraSmart"],
        "name_suffixes": ["", "Farm", "Agro", "Crop", "Field"],
        "problems": [
            "smallholder farmers have no affordable way to detect crop stress or irrigation problems before yield loss becomes visible",
            "produce sold through informal middlemen loses 20-30% of its value before it ever reaches an urban buyer",
            "farmers lack access to real-time weather and market-price data that would let them time planting and selling decisions",
            "cold-chain gaps between farm and market cause a large share of harvested produce to spoil before sale",
        ],
        "solutions": [
            "a subscription service that analyzes weekly satellite imagery of registered plots and sends plain-language SMS alerts",
            "a mobile marketplace connecting farmers directly to urban buyers, cutting out layers of middlemen",
            "an SMS-based advisory service delivering hyper-local weather and market-price alerts to feature phones",
            "a shared cold-storage and logistics network that farmer cooperatives can book by the hour",
        ],
        "targets": [
            "smallholder and mid-size commercial farmers",
            "farmer cooperatives across rural provinces",
            "urban produce buyers and retailers sourcing directly from farms",
        ],
        "differentiators": [
            "a proprietary imagery-processing pipeline tuned specifically for smallholder plot sizes",
            "an SMS-first design that works on any feature phone, no smartphone or app required",
            "logistics partnerships that guarantee last-mile delivery within 48 hours",
        ],
        "tractions": [
            "{n} pilot farmers onboarded with a 78% renewal rate after the first paid month",
            "over {n} farmers and dozens of retail buyers, with repeat purchase rate above 60%",
            "{n} tonnes of produce moved through the platform with under 5% spoilage loss",
        ],
        "business_models": [
            "a flat monthly subscription per hectare monitored, billed via mobile money",
            "a small commission on each transaction between farmer and buyer",
            "a per-booking fee for shared cold-storage and logistics capacity",
        ],
        "teams": [
            "an agronomist co-founder with over a decade of extension-service experience, plus a remote-sensing engineer",
            "founders combining agritech experience abroad with local distribution know-how",
        ],
        "fundings": ["$200,000 seed round", "$500,000 seed round", "$1,000,000 Series A"],
        "revenue_range": (60_000, 500_000),
        "growth_range": (15, 65),
        "margin_range": (2, 24),
        "burn_range": (4_000, 20_000),
    },
    {
        "key": "logistics",
        "industry": "tech",
        "email_domain": "logistica.ao",
        "name_prefixes": ["EntregaJa", "RouteWise", "SwiftDrop", "CargoLink", "LastMileIQ", "DispatchPro"],
        "name_suffixes": ["", "Logistics", "Express", "Route", "Fleet"],
        "problems": [
            "e-commerce sellers rely on informal motorcycle couriers with no tracking or accountability, leading to lost and delayed orders",
            "small delivery fleets plan routes manually, wasting fuel and driver hours on inefficient sequencing",
            "cash-on-delivery settlement between riders and sellers is slow, manual, and prone to disputes",
            "same-day delivery is unavailable outside major city centers because no dispatch network reaches those areas reliably",
        ],
        "solutions": [
            "a dispatch app that assigns vetted riders, gives real-time tracking, and automatically settles cash-on-delivery payments",
            "a route-optimization dashboard that turns a day's delivery addresses into driver-ready optimized routes in seconds",
            "a digital proof-of-delivery and instant-settlement layer that reconciles rider payouts automatically",
            "a shared rider network that lets multiple small sellers pool delivery capacity outside the city center",
        ],
        "targets": [
            "e-commerce sellers who currently rely on informal couriers",
            "regional courier companies and delivery fleet operators",
            "small retailers needing reliable last-mile delivery without owning a fleet",
        ],
        "differentiators": [
            "a routing engine tuned specifically for motorcycle and light-vehicle couriers, unlike generic mapping tools",
            "real-time tracking and accountability that informal courier networks can't match",
            "an instant-settlement layer that eliminates the weekly reconciliation headache riders and sellers both hate",
        ],
        "tractions": [
            "over {n} deliveries processed per week with a 96% on-time rate",
            "{n} fleet customers managing hundreds of vehicles, with average reported fuel savings of 22%",
            "{n} riders active on the platform with same-day payout satisfaction above 90%",
        ],
        "business_models": [
            "a per-delivery fee charged to sellers, with a rider payout deducted automatically",
            "a per-vehicle monthly subscription with usage-based overage pricing for high-volume fleets",
            "a percentage commission on each cash-on-delivery transaction settled through the platform",
        ],
        "teams": [
            "founders with prior experience scaling logistics operations across multiple African markets",
            "a team combining supply-chain software experience with a former fleet-operations manager",
        ],
        "fundings": ["$180,000 seed round", "$600,000 seed round", "$1,200,000 Series A"],
        "revenue_range": (55_000, 420_000),
        "growth_range": (15, 68),
        "margin_range": (1, 18),
        "burn_range": (4_500, 24_000),
    },
    {
        "key": "proptech",
        "industry": "other",
        "email_domain": "startup.ao",
        "name_prefixes": ["ClearRent", "ImobiFacil", "NestKey", "PropVerify", "MoradaDigital", "RentaSegura"],
        "name_suffixes": ["", "Rent", "Homes", "Property", "Imob"],
        "problems": [
            "renters and landlords both lose money to unverified listings, cash-only payments, and disputes with no paper trail",
            "landlords have no digital record of rent payment history, making it hard to vet reliable tenants",
            "property listings are scattered across informal channels, making it slow and risky to find a verified rental",
            "small landlords spend hours each month manually chasing rent payments with no automated reminders",
        ],
        "solutions": [
            "a marketplace where landlords list verified properties and collect rent digitally, with automatic receipts",
            "a shared payment-history ledger that gives both landlords and tenants a trustworthy rental track record",
            "a verification team that physically confirms every new listing before it goes live on the marketplace",
            "an automated rent-collection and reminder system that syncs directly with a landlord's bank account",
        ],
        "targets": [
            "independent landlords and small property managers",
            "renters searching for verified listings in fast-growing urban markets",
            "property management companies overseeing multiple buildings",
        ],
        "differentiators": [
            "an in-house verification team that eliminates the fraud that plagues open listing marketplaces",
            "a shared payment-history record both parties can trust, unlike informal cash arrangements",
            "automated digital receipts that remove the need for manual bookkeeping",
        ],
        "tractions": [
            "{n} verified listings live with hundreds of active tenancies paying rent through the platform monthly",
            "over {n} landlords onboarded with a 90% month-over-month payment collection rate",
            "{n} properties verified across four cities with zero reported fraud incidents",
        ],
        "business_models": [
            "a small percentage fee on each digital rent payment processed",
            "a premium subscription for property managers overseeing multiple units",
            "a one-time verification fee per listing plus an ongoing payment-processing fee",
        ],
        "teams": [
            "founders with backgrounds in proptech and consumer payments",
            "a team combining real-estate operations experience with a fintech product background",
        ],
        "fundings": ["$150,000 seed round", "$450,000 seed round", "$900,000 seed round"],
        "revenue_range": (45_000, 320_000),
        "growth_range": (8, 45),
        "margin_range": (6, 28),
        "burn_range": (3_500, 17_000),
    },
    {
        "key": "hrtech",
        "industry": "tech",
        "email_domain": "trabalho.ao",
        "name_prefixes": ["TalentoUp", "SkillBridge", "ShiftWise", "WorkMatch", "CrewLink", "ObraCerta"],
        "name_suffixes": ["", "Jobs", "Work", "Talent", "Crew"],
        "problems": [
            "skilled tradespeople face chronic underemployment because they lack an efficient way to find short-term contract work",
            "hourly retail and hospitality workers frequently miss shifts because managers build schedules manually with no visibility into availability",
            "employers spend weeks vetting contract workers with no reliable way to verify past job performance",
            "informal labor markets have no shared reputation system, so good workers and bad employers both go unrecognized",
        ],
        "solutions": [
            "a marketplace where workers build a verified profile with completed-job ratings and employers post jobs with automatic shortlists",
            "a scheduling app that lets workers set live availability and auto-fills shifts using a fairness-aware algorithm",
            "a verification pipeline combining certification checks with completed-job ratings that generic job boards lack",
            "a shared reputation ledger that both workers and employers build over time, portable across gigs",
        ],
        "targets": [
            "independent tradespeople and the small contractors who hire them",
            "retail and hospitality chains with 20 or more hourly staff per location",
            "gig workers and the small businesses that hire them on short notice",
        ],
        "differentiators": [
            "a verification process combining certification checks with completed-job ratings that builds real trust",
            "a fairness-aware scheduling engine that measurably reduced no-shows in every pilot location",
            "a portable reputation record that follows the worker across employers, not locked to one platform",
        ],
        "tractions": [
            "over {n} workers placed with a 4.6/5 average employer rating",
            "{n} paying locations with no-show rates cut nearly in half within two months of adoption",
            "{n} verified profiles active with repeat-hire rate above 55%",
        ],
        "business_models": [
            "a placement fee charged to employers per successful hire, with free profiles for workers",
            "a per-location monthly SaaS fee with tiered pricing based on headcount",
            "a small transaction fee on each completed gig booked through the platform",
        ],
        "teams": [
            "founders with staffing-industry and marketplace product backgrounds",
            "a former operations lead at a national retail chain, plus a machine-learning engineer",
        ],
        "fundings": ["$180,000 pre-seed round", "$400,000 seed round", "$700,000 seed round"],
        "revenue_range": (30_000, 280_000),
        "growth_range": (12, 62),
        "margin_range": (0, 20),
        "burn_range": (3_000, 16_000),
    },
    {
        "key": "ecommerce_marketplace",
        "industry": "ecommerce",
        "email_domain": "shop.ao",
        "name_prefixes": ["MercadoJa", "ShopLink", "VendaFacil", "MarketNow", "LojaConecta", "TrocaSegura"],
        "name_suffixes": ["", "Market", "Shop", "Store", "Bazaar"],
        "problems": [
            "small independent sellers can't reach urban buyers without paying steep fees to informal middlemen",
            "shoppers have no way to verify seller reliability before paying, leading to widespread distrust of online buying",
            "small merchants lack the tools to accept digital payments, losing sales to buyers who don't carry cash",
            "sellers with strong local followings on social media have no proper storefront or checkout to convert that following into sales",
        ],
        "solutions": [
            "a curated marketplace with seller verification and buyer-protection guarantees baked into every checkout",
            "a lightweight storefront tool that lets social-media sellers accept digital payments and manage orders in one place",
            "a ratings-and-escrow system that only releases payment to sellers once delivery is confirmed",
            "a mobile-money-native checkout that lets any small seller accept digital payments without a bank account",
        ],
        "targets": [
            "small independent sellers and social-media-first merchants",
            "urban shoppers who want a trustworthy way to buy from local sellers",
            "informal-market vendors ready to move part of their business online",
        ],
        "differentiators": [
            "a seller-verification and buyer-protection layer that generic classifieds sites don't offer",
            "mobile-money-native checkout built for markets where card penetration is low",
            "an escrow system that removes the trust barrier blocking first-time online buyers",
        ],
        "tractions": [
            "over {n} active sellers with month-over-month gross merchandise volume growth above 20%",
            "{n} orders processed with a repeat-buyer rate above 45%",
            "{n} verified sellers onboarded across four cities with dispute rates under 2%",
        ],
        "business_models": [
            "a commission on each transaction plus optional paid placement for sellers",
            "a monthly subscription for sellers wanting advanced storefront tools, free for basic listings",
            "a small payment-processing fee on every mobile-money checkout",
        ],
        "teams": [
            "founders with backgrounds in e-commerce operations and digital payments",
            "a team combining marketplace product experience with a former retail operations manager",
        ],
        "fundings": ["$130,000 pre-seed round", "$380,000 seed round", "$850,000 seed round"],
        "revenue_range": (50_000, 400_000),
        "growth_range": (18, 72),
        "margin_range": (3, 22),
        "burn_range": (4_000, 21_000),
    },
    {
        "key": "energy_cleantech",
        "industry": "other",
        "email_domain": "energia.ao",
        "name_prefixes": ["SolarKap", "LumeGrid", "BrightWatt", "EnergiaJa", "SunLink", "PowerFlow"],
        "name_suffixes": ["", "Energy", "Solar", "Power", "Grid"],
        "problems": [
            "off-grid households rely on costly and unreliable kerosene or diesel generators for basic lighting and power",
            "small businesses lose revenue to frequent grid outages with no affordable backup power option",
            "solar home systems are too expensive for most households to buy outright, and financing options barely exist",
            "rural clinics and schools cannot run essential equipment reliably without a stable power source",
        ],
        "solutions": [
            "a pay-as-you-go solar home system billed via mobile money, replacing kerosene and diesel entirely",
            "a battery-backup subscription service that keeps small businesses running through grid outages",
            "an asset-financing product that lets households pay off a solar system in small mobile-money installments",
            "a solar micro-grid model that powers rural clinics and schools through a shared community subscription",
        ],
        "targets": [
            "off-grid and under-served households",
            "small businesses that lose revenue during frequent power outages",
            "rural clinics and schools without reliable access to the main grid",
        ],
        "differentiators": [
            "a pay-as-you-go billing model that makes solar affordable without a large upfront cost",
            "a collections engine combining solar hardware engineering with fintech experience",
            "remote monitoring that flags underperforming units before customers even notice",
        ],
        "tractions": [
            "systems installed in over {n} households with a 91% on-time payment rate over 18 months",
            "{n} small businesses on the backup-power subscription with under 3% monthly churn",
            "{n} solar units deployed across rural clinics and schools with 99% uptime reported",
        ],
        "business_models": [
            "a pay-as-you-go fee billed via mobile money until the customer owns the unit outright",
            "a flat monthly subscription for backup power capacity",
            "an installment financing fee spread over the system's payback period",
        ],
        "teams": [
            "a team combining solar hardware engineering with fintech collections experience",
            "founders with prior careers in renewable-energy project development",
        ],
        "fundings": ["$220,000 seed round", "$650,000 seed round", "$1,300,000 Series A"],
        "revenue_range": (90_000, 700_000),
        "growth_range": (18, 70),
        "margin_range": (4, 26),
        "burn_range": (7_000, 33_000),
    },
    {
        "key": "fintech_accounting",
        "industry": "finance",
        "email_domain": "fin.ao",
        "name_prefixes": ["ContaCerta", "LivroFacil", "BooksBridge", "FinancasClaras", "LedgerLink", "ContaViva"],
        "name_suffixes": ["", "Books", "Ledger", "Conta", "Finance"],
        "problems": [
            "small and medium businesses still manage finances on paper or spreadsheets, making tax season a scramble every year",
            "SMB owners have no real-time view of cash flow, so they discover financial trouble only after it's already a crisis",
            "invoicing and payment tracking for small businesses is manual, error-prone, and disconnected from actual bank activity",
            "local tax-compliance requirements change often, and most small businesses have no way to keep filings current",
        ],
        "solutions": [
            "cloud accounting and invoicing software with built-in compliance for local tax filing requirements",
            "a real-time cash-flow dashboard that pulls directly from a business's bank and mobile-money accounts",
            "automated invoicing that reconciles against bank activity and flags overdue payments automatically",
            "a compliance-first bookkeeping tool that keeps tax filings current without hiring a full-time accountant",
        ],
        "targets": [
            "small and medium businesses managing finances on paper or spreadsheets",
            "solo entrepreneurs and freelancers who can't afford a dedicated accountant",
            "growing SMBs that have outgrown spreadsheets but can't afford enterprise software",
        ],
        "differentiators": [
            "built-in compliance for local tax requirements that generic international tools ignore",
            "direct bank and mobile-money integrations that keep the ledger accurate without manual entry",
            "pricing designed for small-business budgets, not enterprise finance teams",
        ],
        "tractions": [
            "{n} paying subscribers on monthly plans with churn under 3% per month",
            "over {n} invoices processed with automatic bank reconciliation accuracy above 98%",
            "{n} businesses onboarded in the last two quarters with a 4.5/5 satisfaction score",
        ],
        "business_models": [
            "a monthly subscription tiered by transaction volume",
            "a flat monthly fee plus a small per-invoice processing charge",
            "a freemium model with paid tiers unlocking multi-user access and tax filing",
        ],
        "teams": [
            "founders who previously built accounting tools for the Portuguese SMB market",
            "a team combining accounting-software product experience with a former SMB tax advisor",
        ],
        "fundings": ["$160,000 seed round", "$500,000 seed round", "$1,100,000 Series A"],
        "revenue_range": (85_000, 550_000),
        "growth_range": (15, 60),
        "margin_range": (10, 35),
        "burn_range": (5_000, 22_000),
    },
]


CITY_TAGS = ["", "", "", " Luanda", " Benguela", " Huambo", " 360", " Digital", " Prime", " Hub"]


def pick_vertical(index):
    return VERTICALS[index % len(VERTICALS)]


def make_startup_name(vertical, rng):
    prefix = rng.choice(vertical["name_prefixes"])
    suffix = rng.choice(vertical["name_suffixes"])
    tag = rng.choice(CITY_TAGS)
    base = f"{prefix} {suffix}".strip() if suffix else prefix
    name = f"{base}{tag}".strip()
    return name


def generate_idea(vertical, rng, n_low=200, n_high=6000):
    n = rng.randint(n_low, n_high)
    return {
        "startup_name": make_startup_name(vertical, rng),
        "industry": vertical["industry"],
        "email_domain": vertical["email_domain"],
        "problem": rng.choice(vertical["problems"]),
        "solution": rng.choice(vertical["solutions"]),
        "target_customer": rng.choice(vertical["targets"]),
        "competitive_advantage": rng.choice(vertical["differentiators"]),
        "traction": rng.choice(vertical["tractions"]).format(n=f"{n:,}"),
        "business_model": rng.choice(vertical["business_models"]),
        "team": rng.choice(vertical["teams"]),
        "funding_goal": rng.choice(vertical["fundings"]),
        "revenue_range": vertical["revenue_range"],
        "growth_range": vertical["growth_range"],
        "margin_range": vertical["margin_range"],
        "burn_range": vertical["burn_range"],
    }


def build_pitch_paragraph(idea):
    name = idea["startup_name"]
    return (
        f"{name} addresses a clear pain point: {idea['problem']}. Our solution is "
        f"{idea['solution']}, built specifically for {idea['target_customer']}. What sets us apart is "
        f"{idea['competitive_advantage']}. So far we have {idea['traction']}. Revenue comes from "
        f"{idea['business_model']}. The team behind {name} includes {idea['team']}, and we are raising a "
        f"{idea['funding_goal']} to accelerate growth."
    )


def build_one_liner(idea):
    return f"{idea['startup_name']}: {idea['solution'][0].upper()}{idea['solution'][1:]}."


def build_market_size(idea):
    return (
        f"A large and underserved market for {idea['target_customer']}, with digital penetration still "
        f"low enough to leave significant room for a fast-moving entrant."
    )


def build_use_of_funds(idea):
    return (
        f"Scaling the team, deepening the product for {idea['target_customer']}, and expanding go-to-market "
        f"beyond the current pilot region."
    )


def build_call_to_action(idea):
    return f"Looking to connect with investors who understand {idea['industry']}-focused early-stage bets."
