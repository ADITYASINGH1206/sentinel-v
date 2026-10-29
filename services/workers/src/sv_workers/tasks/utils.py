import asyncio
import concurrent.futures
from collections.abc import Coroutine
from typing import Any


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Safely run an async coroutine from sync Celery tasks.

    If invoked from a thread where an event loop is already running (e.g. FastAPI TestClient),
    dispatches the coroutine to a dedicated thread pool to avoid 'asyncio.run() cannot be
    called from a running event loop' errors.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)
