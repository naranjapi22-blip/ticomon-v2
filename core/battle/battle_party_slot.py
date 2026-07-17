from dataclasses import dataclass


@dataclass(frozen=True)
class BattlePartySlot:
    """A locked battle party slot for one trainer."""

    battle_id: int
    trainer_id: int
    slot: int
    creature_id: int
