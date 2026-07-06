from __future__ import annotations

from dataclasses import dataclass

from core.creature.base_stats import BaseStats
from core.evolution.evolution_chain import EvolutionChain
from core.spawn.spawn_rarity import SpawnRarity
from core.species.species_metadata import SpeciesMetadata
from core.species.variant import Variant


@dataclass(frozen=True)
class Species:
    id: int
    name: str

    types: list[str]
    base_stats: BaseStats

    height: int
    weight: int

    capture_rate: int
    spawn_rarity: SpawnRarity

    metadata: SpeciesMetadata
    evolution_chain: EvolutionChain | None = None
    variants: list[Variant] | None = None
