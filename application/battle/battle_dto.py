from dataclasses import dataclass


@dataclass(frozen=True)
class TeamSelectorOptionDTO:
    collection_number: int
    label: str


@dataclass(frozen=True)
class BattleDisplayDTO:
    battle_id: int
    initiator_trainer_id: int
    opponent_trainer_id: int
    status: str
    initiator_has_party: bool
    opponent_has_party: bool
    winner_trainer_id: int | None
