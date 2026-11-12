# Deployment Guide (Labs 36-37)

## 1. Environment Configuration
1. Copy `.env.example` to `.env` and configure `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `DB_PORT`.
2. Install dependencies:
   pip3 install -r requirements.txt

## 2. Production WSGI Execution (Gunicorn)
Run the application with Gunicorn:
    gunicorn app:app --bind 0.0.0.0:5001 --workers 2

## 3. Cloud Deployment (Render / Railway / Heroku)
1. Push repository to GitHub (`.env` is excluded via `.gitignore`).
2. Provision a managed MySQL instance and restore data via `python3 restore_db.py`.
3. Set environment variables (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`) in your cloud dashboard.
4. Start command uses `Procfile`: `web: gunicorn app:app --bind 0.0.0.0:$PORT`.
5. Verify deployment via `GET /system/health`.
