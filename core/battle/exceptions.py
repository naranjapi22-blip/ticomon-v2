class BattleError(Exception):
    """Base error for battle domain rules."""


class SameBattleParticipant(BattleError):
    """Raised when initiator and opponent are the same trainer."""


class BattleNotParticipant(BattleError):
    """Raised when a trainer is not part of the battle."""


class InvalidBattleState(BattleError):
    """Raised when an action is invalid for the current battle status."""


class InvalidBattleParty(BattleError):
    """Raised when a party selection is invalid."""


class InsufficientTeamSize(BattleError):
    """Raised when a trainer does not have enough team members for battle."""

    def __init__(self, trainer_id: int, required: int) -> None:
        self.trainer_id = trainer_id
        self.required = required
        super().__init__(
            f"Trainer {trainer_id} needs at least {required} team members for battle."
        )
