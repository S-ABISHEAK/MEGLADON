"""RQ-based async job queue. Falls back to a background thread when Redis is
unavailable (e.g. running the API standalone without docker-compose) so the
pipeline still executes asynchronously rather than blocking the request."""
from __future__ import annotations

import threading

from app.config import settings

try:
    import redis
    from rq import Queue

    _redis_conn = redis.from_url(settings.REDIS_URL)
    _redis_conn.ping()
    _queue = Queue("megalodon-pipeline", connection=_redis_conn)
    QUEUE_BACKEND = "redis"
except Exception:
    _queue = None
    QUEUE_BACKEND = "thread"


def enqueue_pipeline(job_id: str, resume_from: str | None = None):
    from app.pipeline.runner import run_pipeline

    if QUEUE_BACKEND == "redis":
        _queue.enqueue(run_pipeline, job_id, resume_from, job_timeout="2h")
    else:
        thread = threading.Thread(target=run_pipeline, args=(job_id, resume_from), daemon=True)
        thread.start()
