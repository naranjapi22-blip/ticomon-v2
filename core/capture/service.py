from abc import ABC, abstractmethod

from core.creature.creature import Creature
from core.opportunity.opportunity import Opportunity


class CaptureService(ABC):
    """Servicio encargado de convertir una Opportunity en una Creature."""

    @abstractmethod
    async def capture(
        self,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> Creature:
        """Captura una Opportunity y devuelve la Creature creada."""
        raise NotImplementedError
