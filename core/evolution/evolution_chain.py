from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionChain:
    id: int

    # especies en la cadena (IDs o Species futuras)
    species: list[int]

    # coste de evolución por especie
    candy_requirements: dict[int, int]

    def stage_of(
        self,
        species_id: int,
    ) -> int:
        """
        Returns the evolutionary stage of a species.

        Stage numbering starts at 1.
        """
        return self.species.index(species_id) + 1
