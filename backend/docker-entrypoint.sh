#!/bin/sh
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding base roles/tenant..."
python -m app.services.seed

echo "Seeding full showcase dataset..."
python -m app.services.demo_data

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
