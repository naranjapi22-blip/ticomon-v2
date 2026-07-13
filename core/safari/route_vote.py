from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Collection, Mapping

from core.safari.domain import SafariRouteVoteStatus
from core.safari.route import SafariRouteOption


class SafariRouteVoteClosed(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SafariRouteVoteResult:
    selected_option: SafariRouteOption
    vote_counts: Mapping[str, int]
    was_tiebreak: bool
    was_random_due_to_no_votes: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "vote_counts",
            MappingProxyType(dict(self.vote_counts)),
        )


class SafariRouteVote:
    def __init__(
        self,
        options: Collection[SafariRouteOption],
        opened_at: datetime,
    ) -> None:
        copied_options = tuple(options)
        if len(copied_options) < 2 or len(copied_options) > 3:
            raise ValueError("route vote requires between 2 and 3 options.")

        option_ids = {option.id for option in copied_options}
        if len(option_ids) != len(copied_options):
            raise ValueError("route option IDs must be unique.")

        source_zones = {option.source_zone for option in copied_options}
        if len(source_zones) != 1:
            raise ValueError("route options must share the same source zone.")

        if opened_at is None:
            raise ValueError("opened_at is required.")

        self._options = copied_options
        self._votes_by_trainer: dict[int, str] = {}
        self._opened_at = opened_at
        self._status = SafariRouteVoteStatus.OPEN

    @property
    def options(self) -> tuple[SafariRouteOption, ...]:
        return self._options

    @property
    def votes_by_trainer(self) -> Mapping[int, str]:
        return MappingProxyType(dict(self._votes_by_trainer))

    @property
    def opened_at(self) -> datetime:
        return self._opened_at

    @property
    def status(self) -> SafariRouteVoteStatus:
        return self._status

    def cast_vote(
        self,
        trainer_id: int,
        option_id: str,
        participant_ids: Collection[int],
    ) -> None:
        self._assert_open()

        if trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")
        if trainer_id not in participant_ids:
            raise ValueError("trainer is not a Safari participant.")
        if option_id not in {option.id for option in self._options}:
            raise ValueError("unknown route option.")

        self._votes_by_trainer[trainer_id] = option_id

    def cancel(self) -> None:
        if self._status == SafariRouteVoteStatus.CANCELLED:
            return

        self._assert_open()
        self._status = SafariRouteVoteStatus.CANCELLED

    def resolve(self, random_source: random.Random) -> SafariRouteVoteResult:
        self._assert_open()

        vote_counts = {option.id: 0 for option in self._options}
        for option_id in self._votes_by_trainer.values():
            vote_counts[option_id] += 1

        no_votes = not self._votes_by_trainer
        if no_votes:
            candidates = list(self._options)
            was_tiebreak = False
        else:
            highest_count = max(vote_counts.values())
            candidates = [
                option
                for option in self._options
                if vote_counts[option.id] == highest_count
            ]
            was_tiebreak = len(candidates) > 1

        selected_option = (
            candidates[0] if len(candidates) == 1 else random_source.choice(candidates)
        )
        self._status = SafariRouteVoteStatus.RESOLVED

        return SafariRouteVoteResult(
            selected_option=selected_option,
            vote_counts=vote_counts,
            was_tiebreak=was_tiebreak,
            was_random_due_to_no_votes=no_votes,
        )

    def _assert_open(self) -> None:
        if self._status != SafariRouteVoteStatus.OPEN:
            raise SafariRouteVoteClosed("Safari route vote is closed.")
