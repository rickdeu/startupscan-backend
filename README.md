# StartupScan — Intelligent Startup Evaluation Platform

StartupScan is a full-stack web platform that automates startup pitch evaluation using artificial intelligence. It combines multimodal input (text, documents, audio, video), local ML models, and GPT integration to produce a score from 0 to 10, a detailed technical report, a visual pitch deck in PDF, and an AI-narrated explainer video.

The system serves entrepreneurs who want to validate ideas, analysts who evaluate opportunities at scale, and investors who need fast deal-flow triage.

---

## Table of contents

1. [Context and purpose](#1-context-and-purpose)
2. [Main features](#2-main-features)
3. [Technical architecture](#3-technical-architecture)
4. [User roles](#4-user-roles)
5. [Data models](#5-data-models)
6. [Prerequisites](#6-prerequisites)
7. [Step-by-step local setup](#7-step-by-step-local-setup)
8. [Environment variables](#8-environment-variables)
9. [Training the AI model](#9-training-the-ai-model)
10. [Using the platform](#10-using-the-platform)
11. [Endpoint reference](#11-endpoint-reference)
12. [Running with Docker Compose](#12-running-with-docker-compose)
13. [Deploying to Render (CI/CD)](#13-deploying-to-render-cicd)
14. [Testing and validation](#14-testing-and-validation)
15. [Troubleshooting](#15-troubleshooting)
16. [Additional technical documentation](#16-additional-technical-documentation)

---

## 1. Context and purpose

### The problem

Manually evaluating startup pitches is slow, subjective, and doesn't scale. An experienced analyst can review a handful of pitches per week; an accelerator receives dozens per month. Feedback is inconsistent across reviewers and rarely includes concrete artifacts the entrepreneur can actually use.

### The solution

StartupScan automates the full cycle: from pitch submission to delivery of presentation-ready artifacts.

1. The entrepreneur submits the pitch in any format (text, PDF, video, audio, or a YouTube link) along with basic financial data.
2. The system extracts, normalizes, and merges all inputs.
3. An ML pipeline (scikit-learn + XGBoost) or GPT generates a success score with categories and explainability.
4. The system automatically produces: a technical PDF report, a visual PDF pitch deck, and an AI-narrated video.
5. Investors can express interest in startups directly on the platform.

### Who it's for

| Profile | What they use |
|---|---|
| Entrepreneur | Pitch submission, idea builder, PDF pitch deck |
| Analyst | Dashboard, batch evaluation (CSV), model management |
| Investor | Deal-flow dashboard, connections with startups |
| General public | Browsing public ideas, star-based feedback |
| Admin | User management, ML models, configuration |

---

## 2. Main features

### Startup evaluation (core)

- Multimodal submission: free text, `.txt`, `.md`, `.csv`, `.pdf`, `.docx`, audio, video, YouTube link
- Financial data: revenue (AOA), growth rate, profit margin, burn rate
- Final score from 0 to 10 with a confidence percentage
- Report with 8 categories: Clarity of Proposal, Value Proposition, Innovation, Feasibility, Scalability, Target Market, Team, Sustainability
- Strengths, weaknesses, and actionable recommendations
- Automatic fallback to the local model when GPT is unavailable

### Batch processing

- CSV upload with multiple pitches
- Asynchronous processing with progress polling
- Download of consolidated results

### Technical PDF report

Generated for every analysis:

- Score, confidence, and categories
- Submitted financial data
- Interpretable analysis
- Actionable recommendations
- Metadata of the model used

### PDF pitch deck (investor slides)

- 1 page = 1 slide
- Executive cover, structured narrative, conclusion
- **Automatic context-based design** (recommended): the system chooses the template based on industry and data
- **Manual premium design**: the user picks from 6 templates — Orbit, Grid, Wave, Diagonal, Aurora, Ribbon

### AI explainer video

Generated from the analysis result:

- **`auto` mode**: tries the D-ID API (realistic presenter) with fallback to a local video
- **`did_only` mode**: D-ID only (fails if the API is unavailable)
- **`local_only` mode**: moviepy + local TTS (no external dependencies)
- Duration between 1 and 3 minutes
- Real-time progress via polling
- Support for presenter gender detection (deepface)

### Idea builder (pitch builder)

- Guided form: problem, solution, target customer, market, business model, competitive advantage, traction, team, funding
- Automatic generation of the narrative pitch (local or GPT)
- Export as PDF
- Publish as a public idea to receive community feedback

### Investor-startup connections

- Investor expresses interest in an analysis with a message
- Entrepreneur sees the interest in the connections hub
- Response cycle: `pending → reviewing → connected / rejected`

### Subscription system (Stripe)

- Three tiers: **Trial** (7-day free trial), **Basic** ($50/month or $400/year), **Pro** ($150/month or $1,200/year)
- **Multi-currency**: prices shown in USD, EUR, and AOA — the user selects the preferred currency on the plans page; the value is stored in `localStorage` and requires no server request
- Checkout via Stripe Checkout Session with support for an existing customer
- Billing management portal via Stripe Billing Portal
- Stripe webhooks: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_*` → automatically update the `Subscription` model in the DB
- Fallback to static payment links when `STRIPE_SECRET_KEY` is not configured

### Email notifications

Every important event sends an email to the user **and** to the administrator (`hangaloandre@gmail.com` in BCC):

| Event | Function |
|---|---|
| Account created | `send_account_created(user, trial_end)` |
| Trial started | `send_trial_started(user, trial_end)` |
| Paid subscription activated | `send_subscription_activated(user, plan)` |
| Plan updated | `send_subscription_updated(user, old_plan, new_plan)` |
| Subscription canceled | `send_subscription_canceled(user, plan_name)` |
| Payment failed | `send_payment_failed(user, plan_name)` |

### ML model management

- Upload of custom datasets (pitches + financials)
- Training and retraining with real-time progress
- Activation of a specific model
- Metadata editing and model removal
- Import of external datasets

---

## 3. Technical architecture

### Stack

| Layer | Technology |
|---|---|
| Web framework | Django 6 + Django REST Framework |
| Frontend | Django Templates + Bootstrap + Chart.js |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Cache and queues | Redis + Celery |
| ML / AI | scikit-learn, XGBoost, pandas, numpy |
| LLM | OpenAI SDK (GPT) |
| Video | moviepy, OpenCV, deepface, D-ID API |
| Audio / TTS | Whisper, librosa, gTTS, edge-tts |
| PDF | ReportLab, pypdf, python-docx |
| Server | Gunicorn + WhiteNoise |
| Deploy | Docker, Render.com, Kubernetes (optional) |

### Data flow

```
User
    │
    ▼
Web form / API
    │
    ▼
Multimodal extraction (pitch_input.py)
  ├── Direct text
  ├── PDF / DOCX / CSV / TXT → text
  ├── Audio → Whisper → text
  └── Video / YouTube → audio → Whisper → text
    │
    ▼
Feature engineering + financial data
    │
    ▼
AI engine
  ├── Local model (scikit-learn / XGBoost)
  └── GPT (fallback / alternative)
    │
    ▼
PitchAnalysis saved to the DB
    │
    ├── Technical PDF report (report_export.py)
    ├── PDF pitch deck (pitch_builder.py)
    └── Narrated video (pitch_video.py)
```

### Asynchronous components

Model training and video generation run as asynchronous jobs. The frontend polls the progress endpoints until completion.

```
Client → POST /model/retrain/ → creates job_id → returns immediately
Client → GET /models/training/progress/<job_id>/ → job status
                                  (repeats until status=completed)
```

---

## 4. User roles

The system uses a role-based access control (RBAC) model.

| Role | Public sign-up | Capabilities |
|---|---|---|
| `admin` | No (Django superuser) | Everything, including user and model management |
| `analista` (analyst) | Yes | Dashboard, evaluation, batch, model management |
| `empreendedor` (entrepreneur) | Yes | Dashboard, pitch submission, idea builder, connections |
| `investidor` (investor) | Yes | Investor dashboard, express interest, connections hub |
| `publico_geral` (general public) | Yes (default) | Browse public ideas, give feedback |

When registering, the user chooses their role. Administrators are created via `createsuperuser` or through the Django admin interface at `/admin/`.

---

## 5. Data models

### PitchAnalysis

The central record for every evaluation.

| Field | Type | Description |
|---|---|---|
| `user` | FK User (nullable) | User who submitted it |
| `startup_name` | CharField | Startup name |
| `industry` | CharField | Sector (tech, health, finance, education, ecommerce, other) |
| `contact_email` | EmailField | Contact email |
| `text` | TextField | Pitch text |
| `audio_file` | FileField | Uploaded audio |
| `video_file` | FileField | Uploaded video |
| `document_file` | FileField | Uploaded document |
| `presenter_face_image_file` | FileField | Presenter photo |
| `youtube_url` | URLField | YouTube link |
| `revenue` | DecimalField | Revenue (AOA) |
| `growth_rate` | FloatField | Growth rate (%) |
| `profit_margin` | FloatField | Profit margin (%) |
| `burn_rate` | DecimalField | Monthly burn rate |
| `success_score` | FloatField | Final score 0–10 |
| `confidence` | FloatField | Prediction confidence (%) |
| `report` | JSONField | Full structured report |
| `status` | CharField | pending / processing / completed / failed |
| `model_version` | CharField | Version of the model used |
| `processing_time` | FloatField | Processing time (s) |

### UserProfile

Extends the Django user with a role.

| Field | Type | Description |
|---|---|---|
| `user` | OneToOneField | Django user |
| `role` | CharField | One of the 5 roles |

### IdeaPitchSubmission

Business idea in the builder.

| Field | Type | Description |
|---|---|---|
| `startup_name` | CharField | Name |
| `one_liner` | CharField | One-sentence pitch |
| `problem` | TextField | Problem it solves |
| `solution` | TextField | Proposed solution |
| `target_customer` | TextField | Target customer |
| `market_size` | TextField | Market size |
| `business_model` | TextField | Business model |
| `competitive_advantage` | TextField | Competitive edge |
| `traction` | TextField | Current traction |
| `team` | TextField | Team |
| `funding_goal` | CharField | Funding goal |
| `use_of_funds` | TextField | Use of funds |
| `model_source` | CharField | local / gpt |
| `status` | CharField | draft / generated |
| `generated_pitch` | JSONField | Generated pitch |

### InvestorConnectionInterest

An investor's interest in a startup.

| Field | Type | Description |
|---|---|---|
| `analysis` | FK PitchAnalysis | Analysis of interest |
| `investor` | FK User | Investor |
| `entrepreneur` | FK User (nullable) | Recipient entrepreneur |
| `status` | CharField | pending / reviewing / connected / rejected / withdrawn |
| `investor_message` | TextField | Investor's message |
| `entrepreneur_reply` | TextField | Entrepreneur's reply |

### SubscriptionPlan

Defines the available plans.

| Field | Type | Description |
|---|---|---|
| `tier` | CharField | `trial` / `basic` / `pro` |
| `interval` | CharField | `month` / `year` / `once` |
| `price_usd` | DecimalField | Price in US dollars |
| `price_eur` | DecimalField | Price in euros (0 = auto-calculated: USD × 0.92) |
| `price_aoa` | DecimalField | Price in kwanzas (0 = auto-calculated: USD × 912) |
| `stripe_price_id` | CharField | Stripe price ID |
| `analyses_per_month` | IntegerField | Analyses/month (0 = unlimited) |
| `gpt_analysis` | BooleanField | Access to the GPT engine |
| `investor_dashboard` | BooleanField | Access to the investor dashboard |

### Subscription

Links users to plans.

| Field | Type | Description |
|---|---|---|
| `user` | OneToOneField | Django user |
| `plan` | FK SubscriptionPlan | Active plan |
| `status` | CharField | `trialing` / `active` / `past_due` / `canceled` / `incomplete` / `inactive` |
| `stripe_customer_id` | CharField | Stripe customer ID |
| `stripe_subscription_id` | CharField | Stripe subscription ID |
| `trial_end` | DateTimeField | Trial expiration date |
| `cancel_at_period_end` | BooleanField | Marked to cancel at period end |

### IdeaPublicFeedback

Community rating of public ideas.

| Field | Type | Description |
|---|---|---|
| `submission` | FK IdeaPitchSubmission | Idea being rated |
| `author` | FK User | Who rated it |
| `stars` | IntegerField | 1 to 5 stars |
| `endorsed` | BooleanField | Endorsement |
| `comment` | TextField | Comment |

---

## 6. Prerequisites

Before you start, make sure you have the following installed:

- **Python 3.10+** — `python --version`
- **pip** — included with Python
- **Git** — to clone the repository
- **Redis** (optional, for Celery) — needed only for asynchronous training and video jobs
- **FFmpeg** (optional) — needed for local video generation

To verify:

```bash
python --version      # Python 3.10.x or higher
pip --version
git --version
redis-cli ping        # PONG (if installed)
ffmpeg -version       # (if installed)
```

> **Note:** The system works without Redis and FFmpeg in basic mode (evaluation, PDF report). Local video and asynchronous processing require both.

---

## 7. Step-by-step local setup

### 7.1 Clone the repository

```bash
git clone https://github.com/rickdeu/startupscan-backend.git
cd startupscan-backend
```

### 7.2 Create and activate a virtual environment

```bash
# Create the virtual environment
python -m venv .venv

# Activate (Linux / macOS)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows cmd)
.venv\Scripts\activate.bat
```

The prompt should show `(.venv)` on the left when the environment is active.

### 7.3 Install dependencies

```bash
pip install -r requirements.txt
```

> Installation may take a few minutes — the project has heavy dependencies such as scikit-learn, moviepy, deepface, and transformers.

### 7.4 Configure environment variables

Create a `.env` file at the project root:

```bash
cp .env.example .env   # if an example exists
# or create it manually
```

Minimal content for local development:

```env
SECRET_KEY=django-insecure-change-this-key-in-production
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

See section [8. Environment variables](#8-environment-variables) for the full list.

### 7.5 Apply database migrations

```bash
python manage.py migrate
```

This creates the `db.sqlite3` file with all the tables.

### 7.6 Create an administrator account

```bash
python manage.py createsuperuser
```

Follow the terminal prompts (username, email, password). This account has full access to the platform and to the admin panel at `/admin/`.

### 7.7 Collect static files

```bash
python manage.py collectstatic --noinput
```

### 7.8 (Optional) Train the initial ML model

The system can evaluate pitches without a pre-trained model (it creates one at runtime), but for better results, train explicitly:

```bash
python manage.py train_model --model-output ai_models/pitch_model.pkl
```

See section [9. Training the AI model](#9-training-the-ai-model) for advanced options.

### 7.9 Start the development server

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit: **http://localhost:8000**

### 7.8 (Optional) Configure subscription plans

```bash
# Create / update plans in the DB and sync with Stripe
python manage.py setup_subscription_plans

# Without Stripe sync (for environments without an API key)
python manage.py setup_subscription_plans --no-sync-stripe
```

### Command summary

```bash
git clone https://github.com/rickdeu/startupscan-backend.git
cd startupscan-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# configure .env (including STRIPE_* and DJANGO_DEBUG=1)
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_subscription_plans
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
```

---

## 8. Environment variables

### Required

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key (REQUIRED in production) | `django-insecure-...` |
| `DJANGO_DEBUG` | Debug mode: `1` for dev, `0` for prod | `1` |

### Optional — Django

| Variable | Description | Default |
|---|---|---|
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts, comma-separated | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Trusted CSRF origins | — |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | — |

### Optional — Database

By default the system uses SQLite. To use PostgreSQL in production:

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Full PostgreSQL connection URL | `postgres://user:pass@host:5432/db` |
| `POSTGRES_USER` | PostgreSQL user | `startupscan` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `password123` |
| `POSTGRES_DB` | Database name | `startupscan` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `DB_IGNORE_SSL` | Ignore SSL on the DB connection: `1` / `0` | `0` |

### Optional — Cache and queues (Celery)

| Variable | Description | Default |
|---|---|---|
| `CELERY_BROKER_URL` | Redis broker URL for Celery | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/0` |

### Stripe (subscriptions and payments)

| Variable | Description | Default |
|---|---|---|
| `STRIPE_SECRET_KEY` | Stripe secret key (sk_live_* or sk_test_*) | — |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (pk_live_* or pk_test_*) | — |
| `STRIPE_WEBHOOK_SECRET` | Webhook validation secret (whsec_*) | — |
| `STRIPE_PAYMENT_LINK_BASIC` | Static payment link URL for the Basic plan | — |
| `STRIPE_PAYMENT_LINK_PRO` | Static payment link URL for the Pro plan | — |

> **Without `STRIPE_SECRET_KEY`:** checkout uses the static payment links if configured. Without either one, an error message is shown to the user.

### Email

| Variable | Description | Default |
|---|---|---|
| `EMAIL_HOST` | SMTP server | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | Sender email | — |
| `EMAIL_HOST_PASSWORD` | Email password | — |
| `SITE_URL` | Base site URL (used in emails) | `https://startupscan.io` |

### Optional — AI and external APIs

| Variable | Description | Effect without the key |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | System uses the local model |
| `OPENAI_MODEL` | GPT model to use | `gpt-4.1-mini` |
| `DID_API_KEY` | D-ID API key (realistic video) | Uses local video generation |
| `DID_API_BASE_URL` | D-ID endpoint | `https://api.d-id.com` |
| `DID_VOICE_ID` | D-ID voice ID | — |
| `EDGE_TTS_VOICE_PT_AO` | Portuguese (Angola) TTS voice | Default edge-tts voice |
| `WHISPER_MODEL` | Whisper model size | `base` |

### Optional — Paths

| Variable | Description | Default |
|---|---|---|
| `AI_MODELS_DIR` | Directory for trained models | `<BASE_DIR>/ai_models` |
| `DATA_DIR` | Directory for datasets | `<BASE_DIR>/data` |

> **Tip:** In development, with no API key at all, every local fallback feature still works. You can evaluate pitches and generate PDFs and local videos at no external cost.

---

## 9. Training the AI model

### How it works

The ML pipeline uses scikit-learn with the following steps:

1. **Data loading**: CSV datasets of pitches and financial data
2. **Feature engineering**: TF-IDF over text + normalized financial features
3. **Ensemble**: RandomForest + GradientBoosting + ExtraTrees (voting)
4. **Cross-validation**: 5-fold KFold
5. **Augmentation**: 60x jitter to enrich scarce data
6. **Serialization**: joblib (`.pkl`)

### Training with the default datasets

```bash
python manage.py train_model --model-output ai_models/pitch_model.pkl
```

### Training with custom datasets

```bash
python manage.py train_model \
  --model-output ai_models/my_model.pkl \
  --pitches-data data/my_pitches.csv \
  --financials-data data/my_financials.csv
```

### Retraining via the web interface

Go to `/models/` (requires the `analista` or `admin` role):

1. Upload the CSV datasets
2. Click "Retrain model"
3. Progress appears in real time
4. Once finished, the new model can be activated

### Expected dataset structure

**pitches.csv** (minimum):
```csv
text,success_score
"Our platform connects...",7.5
"We built a solution...",6.2
```

**financials.csv** (minimum):
```csv
revenue,growth_rate,profit_margin,burn_rate
150000,0.25,0.15,8000
```

---

## 10. Using the platform

### Sign-up and login

1. Go to `http://localhost:8000/register/`
2. Fill in name, email, password, and **choose your role** (entrepreneur, investor, analyst, general public)
3. After registering, you'll be redirected to your role's dashboard
4. To log in again: `http://localhost:8000/login/`

### As an entrepreneur

#### Submit an analysis

1. Go to the menu and click **"Analyze Pitch"** or visit `/analyze/form/`
2. Fill in:
   - Startup name and industry
   - Pitch text (or upload a document/audio/video)
   - Financial data (revenue, growth, margin)
3. Click **"Analyze"** and wait (typically 5–15 seconds)
4. You'll be redirected to the results page with the score and the report

#### View results

On the results page (`/results/<id>/`) you'll find:

- **Success score** (0–10) with a visual chart
- **Confidence level** of the prediction
- **8 categories** evaluated individually
- **Strengths and weaknesses** identified by the model
- Actionable **recommendations** for improvement

#### Download artifacts

- **Technical PDF report**: "Download Report" button → `/results/<id>/pdf/`
- **PDF pitch deck**: "Generate Pitch Deck" button → `/results/<id>/pitch/pdf/`

#### Generate an explainer video

1. On the results page, go to the video section
2. Choose the mode: `auto`, `did_only`, or `local_only`
3. (Optional) Upload the presenter's photo for gender detection
4. Click **"Generate Video"** — progress updates in real time
5. Once finished, the video is available for playback and download

#### Idea builder

1. Go to `/pitch/builder/`
2. Fill in all the idea fields (problem, solution, market, etc.)
3. Click **"Generate Pitch"** — the system creates the narrative content
4. Export as PDF or make the idea public for community feedback

### As an investor

1. Go to the investor dashboard at `/investors/`
2. Browse the available startups with their scores
3. Click **"Express Interest"** on a startup you're interested in
4. Write a message to the entrepreneur
5. Track the connection status at `/connections/`

### As an analyst

1. Use the main dashboard to see all analyses
2. Submit individual or batch analyses (CSV upload at `/batch/analyze/`)
3. Manage ML models at `/models/`
4. Monitor training progress in real time

### As a general public user

1. Browse public ideas at `/ideas/`
2. Open an idea to see the details
3. Give feedback with stars (1–5), an endorsement, and a comment

---

## 11. Endpoint reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| GET | `/login/` | Login page |
| POST | `/login/` | Authenticate |
| GET | `/logout/` | Log out |
| GET | `/register/` | Registration page |
| POST | `/register/` | Create account |
| POST | `/set-language/` | Change interface language |

### Dashboard and navigation

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard (redirects by role) |
| GET | `/home/` | Role-based home |
| GET | `/investors/` | Investor dashboard |

### Pitch analysis

| Method | Endpoint | Description |
|---|---|---|
| GET | `/analyze/form/` | Submission form |
| POST | `/analyze/form/` | Submit pitch for analysis |
| POST | `/analyze/` | Analysis REST API |
| GET | `/results/<id>/` | Results page |
| GET | `/results/<id>/pdf/` | Technical PDF report |
| GET | `/results/<id>/pitch/pdf/` | PDF pitch deck |

### Explainer video

| Method | Endpoint | Description |
|---|---|---|
| POST | `/results/<id>/video/generate/` | Start video generation |
| POST | `/results/<id>/video/detect-gender/` | Detect presenter gender |
| GET | `/results/<id>/video/progress/<job_id>/` | Progress polling |

### Batch processing

| Method | Endpoint | Description |
|---|---|---|
| POST | `/batch/analyze/` | Submit CSV for batch analysis |
| GET | `/batch/status/<batch_id>/` | Batch status |
| GET | `/batch/results/<batch_id>/` | Download results |

### Model management (analyst / admin)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/models/` | Models panel |
| POST | `/model/retrain/` | Start training |
| GET | `/models/training/progress/<job_id>/` | Training progress |
| GET | `/training/status/<task_id>/` | Celery task status |

### Idea builder

| Method | Endpoint | Description |
|---|---|---|
| GET | `/pitch/builder/` | Idea form |
| POST | `/pitch/builder/` | Submit idea |
| GET | `/pitch/builder/<id>/` | View / edit idea |
| GET | `/pitch/builder/<id>/pdf/` | Export idea as PDF |

### Public ideas

| Method | Endpoint | Description |
|---|---|---|
| GET | `/ideas/` | List of public ideas |
| GET | `/ideas/<id>/` | Public idea detail |
| POST | `/ideas/<id>/feedback/` | Submit feedback |

### Connections

| Method | Endpoint | Description |
|---|---|---|
| POST | `/investors/interest/<analysis_id>/` | Express interest |
| GET | `/connections/` | Connections hub |
| POST | `/connections/<interest_id>/update/` | Update connection status |

### Subscriptions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/subscription/plans/` | Plans page (USD / EUR / AOA) |
| POST | `/subscription/checkout/` | Start Stripe checkout |
| GET | `/subscription/checkout/success/` | Post-payment page |
| GET | `/subscription/checkout/cancel/` | Checkout cancellation page |
| GET | `/subscription/billing-portal/` | Stripe billing management portal |
| POST | `/subscription/webhook/stripe/` | Stripe webhook (CSRF exempt) |
| GET | `/subscription/status/` | JSON with current subscription status |

---

## 12. Running with Docker Compose

Docker Compose brings up the full stack: web app, PostgreSQL, Redis, a Celery worker, and Celery Beat scheduler.

### Prerequisites

- Docker Desktop installed and running
- `.env` file configured (see section 8)

### Start all services

```bash
docker-compose up -d
```

Services started:

| Service | Port | Description |
|---|---|---|
| `web` | 8000 | Django app (Gunicorn) |
| `db` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis (cache + Celery broker) |
| `celery-worker` | — | Worker for asynchronous jobs |
| `celery-beat` | — | Periodic task scheduler |

Visit: **http://localhost:8000**

### Useful commands

```bash
# View app logs in real time
docker-compose logs -f web

# Enter the app container
docker-compose exec web bash

# Apply migrations
docker-compose exec web python manage.py migrate

# Create a superuser
docker-compose exec web python manage.py createsuperuser

# Train the initial model
docker-compose exec web python manage.py train_model \
  --model-output ai_models/pitch_model.pkl

# Stop all services
docker-compose down

# Stop and remove all volumes (deletes data)
docker-compose down -v
```

### Persistent volumes

| Volume | Content |
|---|---|
| `postgres_data` | PostgreSQL data |
| `redis_data` | Redis data |
| `media_volume` | User uploads |
| `static_volume` | Collected static files |
| `ai_models_volume` | Trained ML models |

---

## 13. Deploying to Render (CI/CD)

The project has automatic deployment configured to [Render.com](https://render.com) via GitHub Actions.

### Initial setup

1. Create a Web service on Render pointing to this repository
2. Render automatically detects `render.yaml` and configures the service
3. Copy the **Deploy Hook URL** from the Render service settings

### Configure GitHub Secrets

In the GitHub repository, go to **Settings → Secrets → Actions** and add:

| Secret | Value |
|---|---|
| `RENDER_DEPLOY_HOOK_URL` | Render deploy hook URL (required) |
| `RENDER_HEALTHCHECK_URL` | `https://<app>.onrender.com/login/` (optional) |

### Configure environment variables on Render

In the Render dashboard, add the required environment variables:

```
SECRET_KEY=<strong-random-key>
DJANGO_DEBUG=0
DATABASE_URL=<auto-generated-by-render>
OPENAI_API_KEY=<optional>
DID_API_KEY=<optional>
```

### Deploy flow

1. Push to the `main` branch
2. The GitHub Action (`.github/workflows/deploy-render-main.yml`) is triggered
3. Runs tests and checks
4. Calls the Render deploy hook
5. Render pulls the code, installs dependencies, and restarts the service

### Free external exposure (Cloudflare Tunnel)

To expose the local server without deploying:

```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Create the tunnel
cloudflared tunnel create startupscan

# Run the tunnel
cloudflared tunnel run startupscan
```

Add the generated subdomain to `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.

---

## 14. Testing and validation

### Run automated tests

```bash
python manage.py test
```

### Check the Django configuration

```bash
python manage.py check
```

### Functional validation checklist

After setup, validate the main flows:

- [ ] Login and registration for each role
- [ ] Pitch submission with plain text → score generated
- [ ] Pitch submission with a PDF document
- [ ] Download the technical PDF report
- [ ] Generate the PDF pitch deck (automatic design)
- [ ] Generate a video in `local_only` mode
- [ ] Train a model from the panel (analyst/admin)
- [ ] Real-time progress for training and video
- [ ] Idea builder → generation → PDF export
- [ ] Investor → entrepreneur connection flow

---

## 15. Troubleshooting

### Error: `SECRET_KEY environment variable must be set in production`

You're running with `DJANGO_DEBUG=0` without setting `SECRET_KEY`. Add to `.env`:

```env
SECRET_KEY=any-long-random-key
DJANGO_DEBUG=1
```

### D-ID video fails

1. Check that `DID_API_KEY` is set and has credits
2. The presenter's image must be reachable via HTTPS (not local)
3. Test with `local_only` to confirm the issue is only with the D-ID API:
   ```
   mode: local_only
   ```

### PDF doesn't generate

```bash
pip show reportlab   # should show the installed version
```

Also check that the `MEDIA_ROOT` directory has write permission:

```bash
ls -la media/        # should have rw permissions
```

### GPT isn't being used

Confirm that `OPENAI_API_KEY` is set:

```bash
python manage.py shell
>>> import os; print(bool(os.getenv('OPENAI_API_KEY')))
True
```

### Migration fails

```bash
python manage.py migrate --run-syncdb
# or
python manage.py migrate --fake-initial
```

### Submission overlay doesn't disappear

Clear the browser cache (`Ctrl + Shift + R`). The overlay reset is implemented in `base.html`.

### Celery isn't processing jobs

Confirm Redis is running:

```bash
redis-cli ping   # should reply PONG
```

Start the worker manually:

```bash
celery -A startupscan worker --loglevel=info
```

### `ModuleNotFoundError` when importing dependencies

The virtual environment may not be activated:

```bash
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
```

---

## 16. Additional technical documentation

The `docs/` directory contains scripts to generate detailed technical documentation.

### Generate the software engineering PDF

```bash
python docs/generate_engineering_pdf.py
```

Creates: `docs/Software_Engineering_Documentation.pdf`

### Generate the software engineering DOCX

```bash
python docs/generate_engineering_docx.py
```

Creates: `docs/Software_Engineering_Documentation.docx`

### Generate the technical report DOCX

```bash
python docs/generate_technical_report.py
```

Creates: `docs/StartupScan_Technical_Report.docx`

---

## Contributing

1. Fork the repository
2. Create a descriptive branch: `git checkout -b feat/my-feature`
3. Make your changes and test them
4. Push and open a Pull Request against `main`

---

## License

See the `LICENSE` file at the root of the repository.
