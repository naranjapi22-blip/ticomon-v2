from core.battle.battle import Battle
from core.battle.battle_repository import BattleRepository


class InMemoryBattleRepository(BattleRepository):
    """Stores active battle sessions in process memory."""

    def __init__(self) -> None:
        self._battles: dict[int, Battle] = {}
        self._next_id = 1

    async def save(self, battle: Battle) -> Battle:
        if battle.id is None:
            battle._id = self._next_id
            self._next_id += 1

        self._battles[battle.id] = battle
        return battle

    async def get(self, battle_id: int) -> Battle | None:
        return self._battles.get(battle_id)
