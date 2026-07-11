"""Queue parse jobs in KV so the API process does not run scrapes on its event loop."""

from __future__ import annotations

import json
import logging
import time
import uuid

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

QUEUE_KEY = "parser:jobs"
CYCLE_LOCK_KEY = "parser:cycle_lock"
CYCLE_LOCK_TTL = 1800
STALE_RUNNING_SECONDS = 2400


async def enqueue_parse_search(search_id: str) -> str:
    job_id = str(uuid.uuid4())
    payload = json.dumps(
        {
            "id": job_id,
            "type": "parse_search",
            "search_id": search_id,
            "created_at": time.time(),
        },
        ensure_ascii=False,
    )
    redis = await get_redis()
    # Store as list via dedicated key + set membership; SQLite KV has no native list —
    # use job hash + pending set encoded as JSON array.
    raw = await redis.get(QUEUE_KEY)
    jobs: list[str] = []
    if raw:
        try:
            jobs = json.loads(raw)
            if not isinstance(jobs, list):
                jobs = []
        except json.JSONDecodeError:
            jobs = []
    jobs.append(payload)
    await redis.setex(QUEUE_KEY, 86400 * 7, json.dumps(jobs, ensure_ascii=False))
    logger.info("Enqueued parse job %s for search %s", job_id, search_id)
    return job_id


async def pop_parse_jobs(limit: int = 20) -> list[dict]:
    redis = await get_redis()
    raw = await redis.get(QUEUE_KEY)
    if not raw:
        return []
    try:
        jobs = json.loads(raw)
        if not isinstance(jobs, list):
            return []
    except json.JSONDecodeError:
        return []

    taken = jobs[:limit]
    rest = jobs[limit:]
    await redis.setex(QUEUE_KEY, 86400 * 7, json.dumps(rest, ensure_ascii=False))

    parsed: list[dict] = []
    for item in taken:
        try:
            parsed.append(json.loads(item) if isinstance(item, str) else item)
        except (TypeError, json.JSONDecodeError):
            continue
    return parsed


async def acquire_cycle_lock(owner: str, *, ttl: int = CYCLE_LOCK_TTL) -> bool:
    redis = await get_redis()
    existing = await redis.get(CYCLE_LOCK_KEY)
    if existing:
        return False
    await redis.setex(CYCLE_LOCK_KEY, ttl, owner)
    return True


async def release_cycle_lock(owner: str) -> None:
    redis = await get_redis()
    current = await redis.get(CYCLE_LOCK_KEY)
    if current == owner:
        await redis.delete(CYCLE_LOCK_KEY)


def schedule_parse_search(search_id: str) -> None:
    """Backward-compatible sync API: schedule coroutine to enqueue (not scrape)."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(enqueue_parse_search(search_id))
        return
    loop.create_task(enqueue_parse_search(search_id))
