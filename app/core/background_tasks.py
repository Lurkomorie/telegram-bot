"""
Fire-and-forget task helper.

asyncio only keeps a weak reference to a running task, so a bare
`asyncio.create_task(...)` whose result nobody stores can be garbage collected
mid-flight — the coroutine silently stops, and anything it was supposed to
release (a processing lock, a chat action) is left behind. Every background
task in this project goes through `spawn` so a strong reference survives until
the task actually finishes.
"""
import asyncio
from typing import Coroutine, Any, Set

_BACKGROUND_TASKS: Set[asyncio.Task] = set()


def spawn(coro: Coroutine[Any, Any, Any], name: str = "background") -> asyncio.Task:
    """Run a coroutine detached, keeping it alive and logging any failure."""
    task = asyncio.create_task(coro, name=name)
    _BACKGROUND_TASKS.add(task)

    def _done(finished: asyncio.Task) -> None:
        _BACKGROUND_TASKS.discard(finished)
        if finished.cancelled():
            return
        error = finished.exception()
        if error is not None:
            print(f"[BG-TASK] ❌ {finished.get_name()} failed: {type(error).__name__}: {error}")

    task.add_done_callback(_done)
    return task


def pending_count() -> int:
    """How many background tasks are currently in flight (for diagnostics)."""
    return len(_BACKGROUND_TASKS)
