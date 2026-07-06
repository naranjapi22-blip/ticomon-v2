from abc import ABC, abstractmethod

from core.creature.creature import Creature


class CreatureRepository(ABC):
    """Repositorio para la persistencia de Creature."""

    @abstractmethod
    async def save(self, creature: Creature) -> Creature:
        """Persiste una Creature y devuelve la entidad almacenada."""
        raise NotImplementedError
