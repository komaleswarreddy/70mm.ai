import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "70mm_ai_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Standard configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300
)

# Safe fallback task worker executor for environments without running Redis.
def run_background_task(task_func, *args, **kwargs):
    """
    Safely schedules and fires Celery task asynchronously.
    Falls back to immediate thread / sync execution if Celery runs standalone.
    """
    try:
        # Check if broker is reachable. If not, fallback.
        # We can call delay directly or catch broker errors.
        task_func.delay(*args, **kwargs)
        logger.info(f"Successfully enqueued Celery background task: {task_func.__name__}")
    except Exception as e:
        logger.warning(f"Celery broker unavailable. Running fallback execution synchronously. Error: {str(e)}")
        # Execute task synchronously as fallback
        task_func.apply(args=args, kwargs=kwargs)
