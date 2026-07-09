from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionChain:
    """
    Represents an evolutionary chain.

    Responsible for knowing the progression of species and the candy cost
    required for each evolution.
    """

    id: int

    # Ordered species identifiers.
    species: list[int]

    # Candy cost required to evolve FROM a species.
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

    def has_next(
        self,
        species_id: int,
    ) -> bool:
        """
        Returns whether the species has a next evolution.
        """
        return species_id in self.species[:-1]

    def is_final_stage(
        self,
        species_id: int,
    ) -> bool:
        """
        Returns whether the species is the final stage of the chain.
        """
        return not self.has_next(species_id)

    def next_species_of(
        self,
        species_id: int,
    ) -> int:
        """
        Returns the identifier of the next species.

        Raises:
            ValueError: if the species is already the final stage.
        """
        if not self.has_next(species_id):
            raise ValueError("Species has no further evolution.")

        index = self.species.index(species_id)
        return self.species[index + 1]

    def candy_cost_for(
        self,
        species_id: int,
    ) -> int:
        """
        Returns the candy cost required to evolve from the given species.
        """
        if species_id not in self.candy_requirements:
            raise ValueError("Species cannot evolve.")

        return self.candy_requirements[species_id]
