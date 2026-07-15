#!/usr/bin/env bash
set -e

echo "Waiting for the database..."
python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from app.config import settings
for attempt in range(30):
    try:
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"  db not ready ({attempt+1}/30): {exc}")
        time.sleep(2)
sys.exit("Database never became ready.")
PY

echo "Seeding database (projects + researched buyer snapshot)..."
python -m app.seed.seed_db || echo "Seeding step reported an issue; continuing to serve."

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
