import random

from core.species.species import Species


class WeightedSelector:
    """
    Selects species from a collection.

    The selection strategy can evolve over time without
    affecting the rest of the Spawn Engine.
    """

    def select(
        self,
        species: tuple[Species, ...],
        amount: int,
    ) -> tuple[Species, ...]:
        """
        Selects the requested number of species.
        """

        if amount <= 0:
            return ()

        if len(species) < amount:
            raise ValueError("Not enough species available to satisfy the request.")

        return tuple(random.sample(species, k=amount))
