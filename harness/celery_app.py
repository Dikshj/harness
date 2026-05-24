
from celery import Celery
from harness.config import get_settings

settings = get_settings()
celery_app = Celery("harness", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_routes = {"harness.tasks.*": {"queue": "harness"}}
celery_app.autodiscover_tasks(["harness.tasks"])
