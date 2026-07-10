from core.creature.base_stats import BaseStats
from core.evolution.evolution_chain import EvolutionChain
from core.rarity import Rarity
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata
from core.species.variant import Variant


def create_species(
    *,
    id: int = 25,
    name: str = "Pikachu",
    types: list[str] | None = None,
    capture_rate: int = 190,
    generation: int = 1,
    is_baby: bool = False,
    is_legendary: bool = False,
    is_mythical: bool = False,
    variants: list[Variant] | None = None,
    base_stats: BaseStats | None = None,
    evolution_species: list[int] | None = None,
):
    if types is None:
        types = ["electric"]

    if variants is None:
        variants = []

    if evolution_species is None:
        evolution_species = [id]

    return Species(
        id=id,
        pokeapi_id=id,
        name=name,
        types=types,
        base_stats=base_stats
        or BaseStats(
            hp=35,
            attack=55,
            defense=40,
            special_attack=50,
            special_defense=50,
            speed=90,
        ),
        height=4,
        weight=60,
        capture_rate=capture_rate,
        spawn_rarity=Rarity.COMMON,
        metadata=SpeciesMetadata(
            generation=generation,
            is_baby=is_baby,
            is_legendary=is_legendary,
            is_mythical=is_mythical,
        ),
        evolution_chain=EvolutionChain(
            id=1,
            species=evolution_species,
            candy_requirements={},
        ),
        variants=variants,
    )
