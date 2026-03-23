# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

StartupScan.AI is a Django-based multimodal AI startup pitch analysis platform. It uses ML models (scikit-learn, XGBoost, transformers, DeepFace, Whisper) to analyze text, audio, and video pitches along with financial data, predicting a success score (0–10).

### Project structure

- `manage.py` — Django management entry point (at repo root)
- `backend/` — Django project settings package (`settings.py`, `urls.py`, `wsgi.py`)
- `startupscan_api/` — Main Django app (models, views, services, templates)
- `requirements.txt` — ML/processing Python dependencies (root level)
- `ai_models/` — Pre-trained model file (`pitch_model.pkl`)
- `data/` — Training CSV datasets
- `docker-compose.yml` — Docker Compose for PostgreSQL, Redis, Django, Celery

### Missing from requirements.txt

The root `requirements.txt` only contains ML/processing dependencies. The following Django web-framework packages are NOT listed but are required: `django`, `djangorestframework`, `django-cors-headers`, `gunicorn`, `psycopg2-binary`, `celery`, `redis`, `joblib`, `tf-keras`.

### Required services

| Service | How to start | Notes |
|---|---|---|
| PostgreSQL | `sudo pg_ctlcluster 16 main start` | Create DB `startupscan` and user `startupscan` with password `startupscanpass` |
| Redis | `sudo redis-server --daemonize yes` | Default port 6379 |
| Django dev server | `python3 manage.py runserver 0.0.0.0:8000` | Requires env vars below |

### Required environment variables for local dev

```bash
export POSTGRES_USER=startupscan
export POSTGRES_PASSWORD=startupscanpass
export POSTGRES_DB=startupscan
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export DB_IGNORE_SSL=true
```

These must be set before running `manage.py` commands. The settings file falls back to a remote Vultr DB if these aren't set.

### Key commands

- **Run dev server:** `python3 manage.py runserver 0.0.0.0:8000`
- **Run migrations:** `python3 manage.py migrate`
- **Run tests:** `python3 manage.py test`
- **System checks:** `python3 manage.py check`
- **Create superuser:** `python3 manage.py createsuperuser`

### Gotchas

- There is no `backend/requirements.txt` — the Dockerfile references it but only the root `requirements.txt` exists. For local dev, install from root.
- `deepface` requires `tf-keras` package alongside TensorFlow. Without it, imports fail with `ValueError`.
- The `commom_imports.py` warning about "video packages not installed" is benign — the video packages are actually installed but import checks use a different code path.
- `ALLOWED_HOSTS` in settings is `[]`, which works fine with `DEBUG=True` (Django allows localhost automatically).
- The test suite (`startupscan_api/tests.py`) is empty — `python3 manage.py test` reports 0 tests run.
- Celery worker/beat are optional; single-pitch analysis runs synchronously. Only batch analysis requires Celery.
