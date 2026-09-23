"""Standalone RQ worker entrypoint: `python -m app.workers.worker`."""
from redis import Redis
from rq import Worker, Queue

from app.config import settings

if __name__ == "__main__":
    conn = Redis.from_url(settings.REDIS_URL)
    worker = Worker([Queue("megalodon-pipeline", connection=conn)], connection=conn)
    worker.work()
