"""Explicit ownership and safe shutdown for PvP asyncio tasks.

The application service owns startup and action-timeout tasks. The Showdown
controller owns battle, player-listener, and callback tasks. Views own render
tasks. Shutdown follows those ownership boundaries and never cancels or awaits
the task currently performing the shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TaskMetadata:
    owner: str
    role: str
    may_call_cleanup: bool
    cleanup_may_cancel: bool


_task_metadata: dict[int, TaskMetadata] = {}


def _current_task() -> asyncio.Task | None:
    try:
        return asyncio.current_task()
    except RuntimeError:
        return None


def register_task(
    task: asyncio.Task,
    *,
    owner: str,
    role: str,
    may_call_cleanup: bool = False,
    cleanup_may_cancel: bool = True,
) -> asyncio.Task:
    """Register a named task without changing asyncio's task internals."""
    _task_metadata[id(task)] = TaskMetadata(
        owner=owner,
        role=role,
        may_call_cleanup=may_call_cleanup,
        cleanup_may_cancel=cleanup_may_cancel,
    )
    task.add_done_callback(lambda completed: _task_metadata.pop(id(completed), None))
    return task


def _metadata_for(task: asyncio.Task) -> TaskMetadata | None:
    return _task_metadata.get(id(task))


def unique_pending_tasks(
    tasks: Iterable[asyncio.Task | None],
    *,
    current_task: asyncio.Task | None = None,
) -> tuple[asyncio.Task, ...]:
    """Return unfinished asyncio Tasks once each, excluding the current task."""
    current_task = current_task or _current_task()
    unique: dict[int, asyncio.Task] = {}
    for task in tasks:
        if not isinstance(task, asyncio.Task):
            logger.debug("Ignoring non-Task PvP shutdown candidate task=%r", task)
            continue
        if task.done() or task is current_task:
            continue
        unique[id(task)] = task
    return tuple(unique.values())


def _context(
    task: asyncio.Task,
    *,
    current_task: asyncio.Task | None,
    session_id: object | None,
    phase: object | None,
    owner: str,
    reason: str,
) -> dict[str, object | None]:
    metadata = _metadata_for(task)
    return {
        "session_id": session_id,
        "phase": phase,
        "owner": owner,
        "task_owner": metadata.owner if metadata else None,
        "task_role": metadata.role if metadata else None,
        "reason": reason,
        "current_task": current_task.get_name() if current_task else None,
        "target_task": task.get_name(),
        "target_done": task.done(),
        "target_cancelled": task.cancelled(),
    }


async def cancel_task_safely(
    task: asyncio.Task | None,
    *,
    current_task: asyncio.Task | None = None,
    session_id: object | None = None,
    phase: object | None = None,
    owner: str,
    reason: str,
) -> bool:
    """Cancel and await one task, never cancelling the current task."""
    if task is None or not isinstance(task, asyncio.Task) or task.done():
        return False
    current_task = current_task or _current_task()
    context = _context(
        task,
        current_task=current_task,
        session_id=session_id,
        phase=phase,
        owner=owner,
        reason=reason,
    )
    metadata = _metadata_for(task)
    if task is current_task:
        logger.warning("Skipping self-cancellation in PvP task shutdown: %s", context)
        return False
    if metadata is not None and metadata.owner != owner:
        logger.debug("Cancelling task outside requested owner boundary: %s", context)

    logger.debug("Cancelling PvP task: %s", context)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return True
    except Exception:
        logger.exception("Unexpected PvP task shutdown failure: %s", context)
        raise
    return True


async def cancel_tasks_safely(
    tasks: Iterable[asyncio.Task | None],
    *,
    current_task: asyncio.Task | None = None,
    session_id: object | None = None,
    phase: object | None = None,
    owner: str,
    reason: str,
) -> None:
    """Cancel a deduplicated collection without gathering current task."""
    current_task = current_task or _current_task()
    candidates = unique_pending_tasks(tasks, current_task=current_task)
    for task in candidates:
        metadata = _metadata_for(task)
        if metadata is not None and metadata.owner != owner:
            logger.debug(
                "PvP task is outside requested owner boundary before cancellation: %s",
                _context(
                    task,
                    current_task=current_task,
                    session_id=session_id,
                    phase=phase,
                    owner=owner,
                    reason=reason,
                ),
            )
        task.cancel()

    for task in candidates:
        context = _context(
            task,
            current_task=current_task,
            session_id=session_id,
            phase=phase,
            owner=owner,
            reason=reason,
        )
        try:
            await task
        except asyncio.CancelledError:
            continue
        except Exception:
            logger.exception("Unexpected PvP task shutdown failure: %s", context)
            raise
