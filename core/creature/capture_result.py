from dataclasses import dataclass
from core.creature.creature import Creature


@dataclass(frozen=True)
class CaptureResult:
    success: bool
    creature: Creature | None