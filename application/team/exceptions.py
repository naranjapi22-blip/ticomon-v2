class TeamApplicationError(Exception):
    """Base exception for team use-case failures."""


class TeamInsufficientCreatures(TeamApplicationError):
    """Raised when the trainer does not own enough creatures for team actions."""

    def __init__(self, trainer_id: int, minimum: int) -> None:
        super().__init__(
            f"Trainer {trainer_id} must own at least {minimum} creatures "
            "to manage a team."
        )


class TeamCreatureNotFound(TeamApplicationError):
    """Raised when a requested creature does not exist."""

    def __init__(self, collection_number: int) -> None:
        super().__init__(f"Creature #{collection_number} was not found.")


class TeamCreatureNotOwned(TeamApplicationError):
    """Raised when a creature is not owned by the trainer."""

    def __init__(self, trainer_id: int, collection_number: int) -> None:
        super().__init__(
            f"Creature #{collection_number} is not owned by trainer {trainer_id}."
        )


class TeamFull(TeamApplicationError):
    """Raised when the team already has the maximum number of creatures."""

    def __init__(self, maximum: int) -> None:
        super().__init__(f"The team already has the maximum of {maximum} creatures.")


class TeamCreatureAlreadyInTeam(TeamApplicationError):
    """Raised when a creature is already assigned to the team."""

    def __init__(self, collection_number: int) -> None:
        super().__init__(f"Creature #{collection_number} is already in the team.")


class TeamCreatureNotInTeam(TeamApplicationError):
    """Raised when a creature is not currently assigned to the team."""

    def __init__(self, collection_number: int) -> None:
        super().__init__(f"Creature #{collection_number} is not in the team.")
