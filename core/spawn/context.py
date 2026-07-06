from dataclasses import dataclass

from core.spawn.event import Event
from core.spawn.region import Region
from core.spawn.world import World


@dataclass(frozen=True, slots=True)
class SpawnContext:
    """
    Describes the world state when a spawn is requested.
    """

    world: World
    region: Region
    event: Event | None = None
