from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SafariActivityTimingSnapshot:
    selection_deadline: datetime | None
    route_vote_deadline: datetime | None


@dataclass(frozen=True, slots=True)
class SafariActivityMessageSnapshot:
    channel_id: int | None
    message_id: int | None


class SafariActivityTracker:
    def __init__(self) -> None:
        self._selection_deadlines: dict[int, datetime] = {}
        self._route_vote_deadlines: dict[int, datetime] = {}
        self._timers: dict[int, asyncio.Task[None]] = {}
        self._messages: dict[int, SafariActivityMessageSnapshot] = {}

    def get(self, guild_id: int) -> SafariActivityTimingSnapshot:
        return SafariActivityTimingSnapshot(
            selection_deadline=self._selection_deadlines.get(guild_id),
            route_vote_deadline=self._route_vote_deadlines.get(guild_id),
        )

    def set_selection_deadline(self, guild_id: int, deadline: datetime) -> None:
        self._selection_deadlines[guild_id] = deadline

    def set_route_vote_deadline(self, guild_id: int, deadline: datetime) -> None:
        self._route_vote_deadlines[guild_id] = deadline

    def clear_deadlines(self, guild_id: int) -> None:
        self._selection_deadlines.pop(guild_id, None)
        self._route_vote_deadlines.pop(guild_id, None)

    def get_message(self, guild_id: int) -> SafariActivityMessageSnapshot:
        return self._messages.get(guild_id, SafariActivityMessageSnapshot(None, None))

    def set_message(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
    ) -> None:
        self._messages[guild_id] = SafariActivityMessageSnapshot(
            channel_id=channel_id,
            message_id=message_id,
        )

    def clear_message(self, guild_id: int) -> None:
        self._messages.pop(guild_id, None)

    def set_timer_task(self, guild_id: int, task: asyncio.Task[None]) -> None:
        previous = self._timers.get(guild_id)
        if previous is not None and previous is not task and not previous.done():
            previous.cancel()
        self._timers[guild_id] = task

    def clear_timer_task(
        self, guild_id: int, task: asyncio.Task[None] | None = None
    ) -> None:
        current = self._timers.get(guild_id)
        if task is not None and current is not task:
            return
        if current is not None:
            self._timers.pop(guild_id, None)

    def cancel_timer(self, guild_id: int) -> None:
        task = self._timers.pop(guild_id, None)
        if task is not None and not task.done():
            task.cancel()

    def clear(self, guild_id: int) -> None:
        self.cancel_timer(guild_id)
        self.clear_deadlines(guild_id)
        self.clear_message(guild_id)
