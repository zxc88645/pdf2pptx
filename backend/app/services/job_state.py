"""Job state in Redis: status, progress, error, output_path."""
import json
from typing import Optional
from app.core.config import REDIS_URL, JOB_TTL_SECONDS

# Lazy connection
_redis = None


def get_redis():
    global _redis
    if _redis is None:
        import redis
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def job_key(job_id: str) -> str:
    return f"job:{job_id}"


def queue_key() -> str:
    return "queue:jobs"


def set_job(job_id: str, status: str, progress: Optional[str] = None,
            error: Optional[str] = None, output_path: Optional[str] = None) -> None:
    r = get_redis()
    key = job_key(job_id)
    data = {"status": status, "progress": progress or "", "error": error or "", "output_path": output_path or ""}
    r.set(key, json.dumps(data), ex=JOB_TTL_SECONDS)


def update_job(job_id: str, status: Optional[str] = None, progress: Optional[str] = None,
               error: Optional[str] = None, output_path: Optional[str] = None) -> None:
    """Merge updates into existing job state."""
    current = get_job(job_id) or {}
    if status is not None:
        current["status"] = status
    if progress is not None:
        current["progress"] = progress
    if error is not None:
        current["error"] = error
    if output_path is not None:
        current["output_path"] = output_path
    set_job(
        job_id,
        current.get("status", "pending"),
        current.get("progress"),
        current.get("error"),
        current.get("output_path"),
    )


def get_job(job_id: str) -> Optional[dict]:
    r = get_redis()
    key = job_key(job_id)
    raw = r.get(key)
    if not raw:
        return None
    return json.loads(raw)


def push_job(job_id: str) -> None:
    get_redis().rpush(queue_key(), job_id)


def pop_job() -> Optional[str]:
    return get_redis().lpop(queue_key())
