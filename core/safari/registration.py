from __future__ import annotations

from datetime import datetime
from typing import Iterable

from core.safari.domain import SafariRegistrationStatus


class SafariRegistrationClosed(ValueError):
    pass


class SafariRegistration:
    def __init__(
        self,
        guild_id: int,
        unlock_id: int,
        participant_ids: Iterable[int],
        opened_at: datetime,
        status: SafariRegistrationStatus = SafariRegistrationStatus.OPEN,
    ) -> None:
        if guild_id <= 0:
            raise ValueError("guild_id must be positive.")

        if unlock_id <= 0:
            raise ValueError("unlock_id must be positive.")

        if opened_at is None:
            raise ValueError("opened_at is required.")

        participants = set(participant_ids)
        if any(trainer_id <= 0 for trainer_id in participants):
            raise ValueError("participant IDs must be positive.")

        self._guild_id = guild_id
        self._unlock_id = unlock_id
        self._participant_ids = participants
        self._opened_at = opened_at
        self._status = status

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def unlock_id(self) -> int:
        return self._unlock_id

    @property
    def participant_ids(self) -> frozenset[int]:
        return frozenset(self._participant_ids)

    @property
    def opened_at(self) -> datetime:
        return self._opened_at

    @property
    def status(self) -> SafariRegistrationStatus:
        return self._status

    @property
    def participant_count(self) -> int:
        return len(self._participant_ids)

    @property
    def is_empty(self) -> bool:
        return not self._participant_ids

    def join(
        self,
        trainer_id: int,
    ) -> None:
        self._assert_open()

        if trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")

        if trainer_id in self._participant_ids:
            return

        self._participant_ids.add(trainer_id)

    def leave(self, trainer_id: int) -> bool:
        self._assert_open()

        if trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")

        if trainer_id not in self._participant_ids:
            return False

        self._participant_ids.remove(trainer_id)
        return True

    def cancel(self) -> None:
        if self._status == SafariRegistrationStatus.CANCELLED:
            return

        self._assert_open()
        self._status = SafariRegistrationStatus.CANCELLED

    def consume(self) -> None:
        if self._status == SafariRegistrationStatus.CONSUMED:
            return

        self._assert_open()
        self._status = SafariRegistrationStatus.CONSUMED

    def has_minimum(self, minimum_participants: int) -> bool:
        if minimum_participants <= 0:
            raise ValueError("minimum_participants must be positive.")

        return self.participant_count >= minimum_participants

    def _assert_open(self) -> None:
        if self._status != SafariRegistrationStatus.OPEN:
            raise SafariRegistrationClosed("Safari registration is closed.")
