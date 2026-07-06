from core.creature.base_stats import BaseStats
from core.spawn.spawn_rarity import SpawnRarity
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata


class SpeciesMapper:
    @staticmethod
    def from_row(row) -> Species:
        return Species(
            id=row["id"],
            name=row["name"],
            types=[row["type_1"], row["type_2"]] if row["type_2"] else [row["type_1"]],
            base_stats=BaseStats(
                hp=row["hp"],
                attack=row["attack"],
                defense=row["defense"],
                special_attack=row["special_attack"],
                special_defense=row["special_defense"],
                speed=row["speed"],
            ),
            height=row["height"],
            weight=row["weight"],
            capture_rate=row["capture_rate"],
            spawn_rarity=SpawnRarity(row["spawn_rarity"]),
            metadata=SpeciesMetadata(
                generation=row["generation"],
                is_baby=row["is_baby"],
                is_legendary=row["is_legendary"],
                is_mythical=row["is_mythical"],
            ),
            evolution_chain=None,
            variants=[],
        )
