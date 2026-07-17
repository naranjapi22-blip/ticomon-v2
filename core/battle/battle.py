from __future__ import annotations

from datetime import datetime

from core.battle.battle_party_slot import BattlePartySlot
from core.battle.battle_status import BattleStatus
from core.battle.exceptions import (
    BattleNotParticipant,
    InvalidBattleParty,
    InvalidBattleState,
    SameBattleParticipant,
)

PARTY_SIZE = 3


class Battle:
    """Two-trainer PvP battle session with private party selection."""

    def __init__(
        self,
        *,
        initiator_trainer_id: int,
        opponent_trainer_id: int,
        created_at: datetime,
    ) -> None:
        self._id: int | None = None
        self._initiator_trainer_id = initiator_trainer_id
        self._opponent_trainer_id = opponent_trainer_id
        self._created_at = created_at
        self._status = BattleStatus.SELECTING
        self._winner_trainer_id: int | None = None
        self._party_slots: dict[int, tuple[int, ...]] = {}

    @classmethod
    def create(
        cls,
        initiator_trainer_id: int,
        opponent_trainer_id: int,
        created_at: datetime,
    ) -> "Battle":
        if initiator_trainer_id == opponent_trainer_id:
            raise SameBattleParticipant()

        return cls(
            initiator_trainer_id=initiator_trainer_id,
            opponent_trainer_id=opponent_trainer_id,
            created_at=created_at,
        )

    @classmethod
    def reconstitute(
        cls,
        *,
        battle_id: int,
        initiator_trainer_id: int,
        opponent_trainer_id: int,
        created_at: datetime,
        status: BattleStatus,
        winner_trainer_id: int | None,
        party_slots: list[BattlePartySlot],
    ) -> "Battle":
        battle = cls(
            initiator_trainer_id=initiator_trainer_id,
            opponent_trainer_id=opponent_trainer_id,
            created_at=created_at,
        )
        battle._id = battle_id
        battle._status = status
        battle._winner_trainer_id = winner_trainer_id

        for party_slot in party_slots:
            trainer_party = battle._party_slots.setdefault(
                party_slot.trainer_id,
                (),
            )
            slots = list(trainer_party)
            while len(slots) < party_slot.slot:
                slots.append(0)
            slots[party_slot.slot - 1] = party_slot.creature_id
            battle._party_slots[party_slot.trainer_id] = tuple(slots)

        return battle

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def initiator_trainer_id(self) -> int:
        return self._initiator_trainer_id

    @property
    def opponent_trainer_id(self) -> int:
        return self._opponent_trainer_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def status(self) -> BattleStatus:
        return self._status

    @property
    def winner_trainer_id(self) -> int | None:
        return self._winner_trainer_id

    @property
    def is_terminal(self) -> bool:
        return self._status in {
            BattleStatus.COMPLETED,
            BattleStatus.CANCELLED,
        }

    @property
    def is_ready(self) -> bool:
        return self._status is BattleStatus.READY

    def party_for(self, trainer_id: int) -> tuple[int, ...] | None:
        self._ensure_participant(trainer_id)
        party = self._party_slots.get(trainer_id)
        if party is None or len(party) != PARTY_SIZE:
            return None
        return party

    def has_party(self, trainer_id: int) -> bool:
        party = self._party_slots.get(trainer_id)
        return party is not None and len(party) == PARTY_SIZE

    def set_party(
        self,
        trainer_id: int,
        creature_ids: tuple[int, ...],
    ) -> None:
        if self._status is not BattleStatus.SELECTING:
            raise InvalidBattleState()

        self._ensure_participant(trainer_id)

        if len(creature_ids) != PARTY_SIZE:
            raise InvalidBattleParty(
                f"Battle party must contain exactly {PARTY_SIZE} creatures."
            )

        if len(set(creature_ids)) != PARTY_SIZE:
            raise InvalidBattleParty("Battle party creatures must be unique.")

        self._party_slots[trainer_id] = creature_ids

        if self.has_party(self._initiator_trainer_id) and self.has_party(
            self._opponent_trainer_id
        ):
            self._status = BattleStatus.READY

    def start(self) -> None:
        if self._status is not BattleStatus.READY:
            raise InvalidBattleState()

        self._status = BattleStatus.IN_PROGRESS

    def complete(self, winner_trainer_id: int) -> None:
        if self._status is not BattleStatus.IN_PROGRESS:
            raise InvalidBattleState()

        self._ensure_participant(winner_trainer_id)
        self._status = BattleStatus.COMPLETED
        self._winner_trainer_id = winner_trainer_id

    def cancel(self, actor_trainer_id: int) -> None:
        if self.is_terminal:
            raise InvalidBattleState()

        self._ensure_participant(actor_trainer_id)
        self._status = BattleStatus.CANCELLED

    def _ensure_participant(self, trainer_id: int) -> None:
        if trainer_id not in {
            self._initiator_trainer_id,
            self._opponent_trainer_id,
        }:
            raise BattleNotParticipant()
