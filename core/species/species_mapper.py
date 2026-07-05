from core.species.species import Species
from core.creature.base_stats import BaseStats


class SpeciesMapper:

    @staticmethod
    def from_row(row) -> Species:
        return Species(
            id=row[0],
            name=row[2],
            types=[row[3], row[4]] if row[4] else [row[3]],
            base_stats=BaseStats(
                hp=row[10],
                attack=row[11],
                defense=row[12],
                special_attack=row[13],
                special_defense=row[14],
                speed=row[15],
            ),
            height=row[5],
            weight=row[6],
            capture_rate=row[7],
        )