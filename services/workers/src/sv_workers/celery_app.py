from celery import Celery
from sv_core.settings import settings

celery_app = Celery(
    "sentinel_v_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "sv_workers.tasks.ingest.*": {"queue": "ingest"},
        "sv_workers.tasks.preprocess.*": {"queue": "preprocess"},
        "sv_workers.tasks.gpu.*": {"queue": "gpu"},
        "sv_workers.tasks.finalize.*": {"queue": "finalize"},
        "sv_workers.tasks.anchor.*": {"queue": "anchor"},
        "sv_workers.tasks.monitor.*": {"queue": "monitor"},
    },
)
