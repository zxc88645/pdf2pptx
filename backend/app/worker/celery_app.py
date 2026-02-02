"""Celery app and task for PDF->PPT pipeline."""
from celery import Celery
from app.core.config import REDIS_URL

app = Celery("pdf2pptx", broker=REDIS_URL, backend=REDIS_URL)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.task_track_started = True
app.conf.task_time_limit = 3600  # 1h
app.conf.worker_prefetch_multiplier = 1


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_pipeline_task(self, job_id: str):
    from app.worker.pipeline import run_pipeline
    run_pipeline(job_id)
