from poke_env.battle.move import Move

from core.battle.ports.damage_calculator import (
    LearnsetProvider,
    SpeciesLearnset,
    SpeciesLearnsetQuery,
)
from core.battle.rules.move_policy import MoveData, move_data_from_poke_env
from infrastructure.battle.poke_env.showdown_species_resolver import (
    _gen9_data,
    resolve_showdown_id,
)


class PokeEnvLearnsetProvider(LearnsetProvider):
    def get_learnset(self, query: SpeciesLearnsetQuery) -> SpeciesLearnset:
        species_showdown_id = resolve_showdown_id(
            pokeapi_id=query.pokeapi_id,
            species_name=query.species_name,
        )
        learnsets = _gen9_data().learnset
        raw = learnsets.get(species_showdown_id)
        if raw is None:
            return SpeciesLearnset(
                species_showdown_id=species_showdown_id,
                moves={},
            )

        move_ids = raw.get("learnset", raw) if isinstance(raw, dict) else {}
        if not isinstance(move_ids, dict):
            return SpeciesLearnset(
                species_showdown_id=species_showdown_id,
                moves={},
            )

        result: dict[str, MoveData] = {}
        for move_id in move_ids:
            try:
                move = Move(move_id, gen=9)
            except Exception:
                continue
            result[move_id] = move_data_from_poke_env(move_id, move)

        return SpeciesLearnset(
            species_showdown_id=species_showdown_id,
            moves=result,
        )
