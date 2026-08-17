#!/bin/sh
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding demo data..."
python -m app.services.seed

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
