from enum import Enum


class BattleStatus(str, Enum):
    """Lifecycle states for a PvP battle session."""

    SELECTING = "selecting"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
