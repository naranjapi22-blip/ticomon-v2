from enum import Enum


class TradeStatus(str, Enum):
    """Lifecycle states for a trade negotiation."""

    DRAFT = "draft"
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
