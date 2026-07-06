from dataclasses import dataclass

from core.spawn.rule import Rule


@dataclass(frozen=True, slots=True)
class SpawnProfile:
    """
    Defines the configuration used by the Spawn Engine.
    """

    opportunity_count: int
    rules: tuple[Rule, ...] = ()
