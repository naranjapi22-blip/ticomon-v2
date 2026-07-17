from functools import lru_cache

from poke_env.battle.move import Move
from poke_env.data import GenData

from core.battle.ports.damage_calculator import LearnsetProvider
from core.battle.rules.move_policy import MoveData, move_data_from_poke_env


@lru_cache(maxsize=512)
def _gen9_data() -> GenData:
    return GenData.from_gen(9)


class PokeEnvLearnsetProvider(LearnsetProvider):
    def get_learnset(self, species_showdown_id: str) -> dict[str, MoveData]:
        learnsets = _gen9_data().learnset
        raw = learnsets.get(species_showdown_id)
        if raw is None:
            return {}

        move_ids = raw.get("learnset", raw) if isinstance(raw, dict) else {}
        if not isinstance(move_ids, dict):
            return {}

        result: dict[str, MoveData] = {}
        for move_id in move_ids:
            try:
                move = Move(move_id, gen=9)
            except Exception:
                continue
            result[move_id] = move_data_from_poke_env(move_id, move)

        return result
