class TradeError(Exception):
    """Base exception for trade domain errors."""


class SameTradeParticipant(TradeError):
    """Raised when a trainer attempts to trade with itself."""


class TradeNotParticipant(TradeError):
    """Raised when an actor does not belong to the trade."""


class InvalidTradeState(TradeError):
    """Raised when an action is not allowed in the current lifecycle state."""


class IncompleteTradeOffer(TradeError):
    """Raised when both participants have not supplied an offer."""


class DuplicateTradeCreature(TradeError):
    """Raised when a creature appears more than once in a trade."""


class EmptyTradeOffer(TradeError):
    """Raised when an offer contains no creatures."""


class TradeOfferMustContainExactlyOneCreature(TradeError):
    """Raised when an offer does not contain exactly one creature."""


class InvalidTradeExpiry(TradeError):
    """Raised when a trade expiry is not later than its creation time."""


class TradeExecutionConflict(TradeError):
    """Raised when final atomic trade validation cannot be satisfied."""
