from collections import defaultdict
from functools import lru_cache

from poke_env.data import GenData

from core.battle.species_id import to_species_showdown_id
from core.species.regional_species import is_regional_pokeapi_id


@lru_cache(maxsize=1)
def _gen9_data() -> GenData:
    return GenData.from_gen(9)


@lru_cache(maxsize=1)
def _pokeapi_num_to_showdown_ids() -> dict[int, tuple[str, ...]]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for showdown_id, entry in _gen9_data().pokedex.items():
        num = entry.get("num")
        if num is not None and num > 0:
            grouped[num].append(showdown_id)
    return {num: tuple(ids) for num, ids in grouped.items()}


def resolve_showdown_id(*, pokeapi_id: int, species_name: str) -> str:
    normalized = to_species_showdown_id(species_name)
    learnsets = _gen9_data().learnset

    if is_regional_pokeapi_id(pokeapi_id):
        return normalized

    candidates = _pokeapi_num_to_showdown_ids().get(pokeapi_id, ())
    if normalized in candidates:
        return normalized

    learnset_candidates = [
        candidate for candidate in candidates if candidate in learnsets
    ]
    if len(learnset_candidates) == 1:
        return learnset_candidates[0]

    if learnset_candidates:
        return min(learnset_candidates, key=len)

    if normalized in learnsets:
        return normalized

    return normalized
