from __future__ import annotations

from dataclasses import dataclass

from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.species.species import Species
from core.species.variant import Variant


@dataclass
class Opportunity:
    """
    Represents a temporary interaction opportunity within the world.

    An Opportunity already knows all individual characteristics of the future
    Creature, but does not yet belong to a Trainer.
    """

    # Species identity.
    species: Species

    # Individual characteristics.
    ivs: IVs
    size: Size
    nature: Nature
    is_shiny: bool

    # Initial visual form.
    initial_form: Variant | None

    # Allowed interaction.
    interaction: str

    # Capture state.
    failed_attempts: int = 0
