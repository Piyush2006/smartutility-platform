"""
Celery worker + beat entrypoint (CLAUDE.md §30). Run with:

    celery -A app.tasks.celery_app worker --loglevel=info
    celery -A app.tasks.celery_app beat --loglevel=info

Both require REDIS_URL to point at a running Redis (see docker-compose.yml
'redis' service) -- not available in every dev environment, which is why
every schedule-driven job also has a synchronous "Generate Now" API route
that calls the same service function directly (see app/services/*_engine.py).
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("utilityos", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.beat_schedule = {
    "run-due-meter-schedules-every-5-min": {"task": "app.tasks.meter_tasks.run_due_meter_schedules", "schedule": crontab(minute="*/5")},
    "run-due-bill-schedules-every-5-min": {"task": "app.tasks.billing_tasks.run_due_bill_schedules", "schedule": crontab(minute="*/5")},
    "run-due-vee-schedules-every-minute": {"task": "app.tasks.vee_tasks.run_due_vee_schedules", "schedule": crontab(minute="*")},
}
celery_app.conf.timezone = "UTC"
