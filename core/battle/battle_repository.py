from abc import ABC, abstractmethod

from core.battle.battle import Battle


class BattleRepository(ABC):
    """Persistence port for battle sessions."""

    @abstractmethod
    async def save(self, battle: Battle) -> Battle:
        raise NotImplementedError

    @abstractmethod
    async def get(self, battle_id: int) -> Battle | None:
        raise NotImplementedError
