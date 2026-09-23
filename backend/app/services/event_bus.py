"""
Real-time stage event bus. Pipeline stages publish events via Redis pub/sub
(or an in-process fallback queue when Redis is unavailable, e.g. local demo
without docker-compose) and the WebSocket endpoint relays them verbatim to
the frontend. No timer-based fake progress anywhere in this path.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict

from app.config import settings

CHANNEL_PREFIX = "megalodon:job:"

try:
    import redis

    _redis_client = redis.from_url(settings.REDIS_URL)
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    _redis_client = None
    REDIS_AVAILABLE = False

# in-process fallback: per-job list of events, used only when redis is down
_fallback_store: dict[str, list[dict]] = defaultdict(list)


def publish_event(job_id: str, event: dict) -> None:
    event = {**event, "ts": time.time()}
    if REDIS_AVAILABLE:
        _redis_client.publish(CHANNEL_PREFIX + job_id, json.dumps(event))
        _redis_client.rpush(f"{CHANNEL_PREFIX}{job_id}:log", json.dumps(event))
        _redis_client.expire(f"{CHANNEL_PREFIX}{job_id}:log", 60 * 60 * 24)
    else:
        _fallback_store[job_id].append(event)


def get_history(job_id: str) -> list[dict]:
    if REDIS_AVAILABLE:
        raw = _redis_client.lrange(f"{CHANNEL_PREFIX}{job_id}:log", 0, -1)
        return [json.loads(r) for r in raw]
    return list(_fallback_store[job_id])


async def subscribe(job_id: str):
    """Async generator yielding events for a job in real time."""
    if REDIS_AVAILABLE:
        pubsub = _redis_client.pubsub()
        pubsub.subscribe(CHANNEL_PREFIX + job_id)
        try:
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    yield json.loads(message["data"])
                else:
                    await asyncio.sleep(0.25)
        finally:
            pubsub.close()
    else:
        last_index = 0
        while True:
            events = _fallback_store[job_id]
            while last_index < len(events):
                yield events[last_index]
                last_index += 1
            await asyncio.sleep(0.25)
