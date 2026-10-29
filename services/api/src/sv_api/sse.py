import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sv_core.settings import settings

# In-memory subscriber registry for environments without live Redis
_local_subscribers: dict[str, list] = defaultdict(list)


async def publish_progress(analysis_id: str, stage: str, pct: int, message: str) -> None:
    """Publish a progress event for an active analysis."""
    payload = json.dumps({"stage": stage, "pct": pct, "message": message})

    # 1. Try publishing to Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.publish(f"sv:analysis:{analysis_id}:events", payload)
        await r.aclose()
    except Exception:
        pass

    # 2. Also dispatch to local queues if active
    if analysis_id in _local_subscribers:
        for q in _local_subscribers[analysis_id]:
            await q.put(payload)


async def subscribe_events(analysis_id: str) -> AsyncGenerator[str, None]:
    """Subscribe to progress SSE events for a specific analysis."""
    queue: asyncio.Queue = asyncio.Queue()
    _local_subscribers[analysis_id].append(queue)

    redis_sub = None
    try:
        # Check Redis subscription
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_sub = r.pubsub()
            await redis_sub.subscribe(f"sv:analysis:{analysis_id}:events")
        except Exception:
            redis_sub = None

        while True:
            # Check local queue first
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield f"event: progress\ndata: {msg}\n\n"
                continue
            except TimeoutError:
                pass

            # Check Redis pub/sub if active
            if redis_sub is not None:
                try:
                    redis_msg = await redis_sub.get_message(
                        ignore_subscribe_messages=True, timeout=0.5
                    )
                    if redis_msg and "data" in redis_msg:
                        yield f"event: progress\ndata: {redis_msg['data']}\n\n"
                except Exception:
                    pass

            # Heartbeat ping
            yield ": ping\n\n"

    finally:
        if analysis_id in _local_subscribers and queue in _local_subscribers[analysis_id]:
            _local_subscribers[analysis_id].remove(queue)
        if redis_sub is not None:
            try:
                await redis_sub.unsubscribe()
                await redis_sub.close()
            except Exception:
                pass
