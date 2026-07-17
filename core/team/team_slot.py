from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TeamSlot:
    """
    Represents one creature assigned to a trainer team slot.
    """

    trainer_id: int
    slot: int
    creature_id: int
    id: int | None = None
