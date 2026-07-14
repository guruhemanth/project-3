"""Celery application (broker/backend = Valkey/Redis)."""
from __future__ import annotations

from celery import Celery

from ..config import settings

celery_app = Celery("subtrack", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    beat_schedule={
        # Daily sweep of upcoming trial-end / renewal dates.
        "send-daily-alerts": {
            "task": "app.tasks.alert_tasks.send_daily_alerts",
            "schedule": 86400.0,  # 24h
        },
    },
)

# Discover task modules so @celery_app.task-decorated tasks are registered.
celery_app.autodiscover_tasks(["app.tasks"])
