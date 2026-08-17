# UtilityOS

Multi-tenant utility billing platform. See `CLAUDE.md` for the full
product spec (derived from `Utilities.xlsx`) and `IMPLEMENTATION_STATUS.md`
for current build progress.

Stack: Next.js/TypeScript frontend, FastAPI/SQLAlchemy/Alembic backend,
PostgreSQL, Redis + Celery for background jobs, JWT auth, Docker Compose.

## Run with Docker (recommended)

```bash
docker compose up --build
# first run only, once postgres is healthy:
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.services.seed
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Demo logins: see `SEED_CREDENTIALS.md`

`celery-worker` + `celery-beat` services run scheduled meter/bill/VEE
runs automatically every few minutes (see `app/tasks/`). Every
schedule-driven action also has a manual "Generate Run" button in the
UI, so the demo doesn't depend on the worker being up.

## Run locally without Docker

Requires a running PostgreSQL instance; point `DATABASE_URL` at it.

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL if not using the defaults
alembic upgrade head
python -m app.services.seed
uvicorn app.main:app --reload

# frontend (separate shell)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

Backend tests run against an isolated SQLite database (see
`backend/tests/conftest.py`) so they need no external services;
production/dev runtime always uses PostgreSQL.

## Notes on this build environment

This repository was built in a sandbox without Docker or a local
PostgreSQL install. The full stack (migrations, seed, API, frontend
login → dashboard) was verified end-to-end against SQLite as a stand-in,
and the Alembic migration was checked for zero drift against the ORM
models with Postgres-portable SQL. It has **not** been run against real
Postgres/Docker yet — do that as the first step wherever Docker is
available, per the Docker instructions above.
