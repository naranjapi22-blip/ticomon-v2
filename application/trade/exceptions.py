class TradeApplicationError(Exception):
    """Base exception for trade use-case failures."""


class TradeNotFound(TradeApplicationError):
    """Raised when a requested trade does not exist."""

    def __init__(self, trade_id: int) -> None:
        super().__init__(f"Trade {trade_id} was not found.")


class TradeTrainerNotFound(TradeApplicationError):
    """Raised when a trade participant does not exist."""

    def __init__(self, trainer_id: int) -> None:
        super().__init__(f"Trainer {trainer_id} was not found.")


class TradeCreatureNotFound(TradeApplicationError):
    """Raised when an offered creature does not exist."""

    def __init__(self, creature_id: int) -> None:
        super().__init__(f"Creature {creature_id} was not found.")


class TradeCreatureNotOwned(TradeApplicationError):
    """Raised when an offered creature has a different current owner."""

    def __init__(self, trainer_id: int, creature_id: int) -> None:
        super().__init__(
            f"Creature {creature_id} is not owned by trainer {trainer_id}."
        )
