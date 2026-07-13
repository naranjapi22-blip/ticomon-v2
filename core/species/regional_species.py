from core.species.species import Species

REGIONAL_POKEAPI_IDS: frozenset[int] = frozenset(
    {
        10091,
        10092,
        10100,
        10101,
        10102,
        10103,
        10104,
        10105,
        10106,
        10107,
        10108,
        10109,
        10110,
        10111,
        10112,
        10113,
        10114,
        10115,
        10161,
        10162,
        10163,
        10164,
        10165,
        10166,
        10167,
        10168,
        10172,
        10173,
        10174,
        10175,
        10176,
        10179,
        10180,
        10229,
        10230,
        10231,
        10232,
        10233,
        10234,
        10235,
        10236,
        10237,
        10238,
        10239,
        10240,
        10241,
        10242,
        10243,
        10244,
        10250,
        10251,
        10252,
    }
)


def is_regional_pokeapi_id(pokeapi_id: int) -> bool:
    if pokeapi_id <= 0:
        raise ValueError("pokeapi_id must be positive.")

    return pokeapi_id in REGIONAL_POKEAPI_IDS


def is_regional_species(species: Species) -> bool:
    return is_regional_pokeapi_id(species.pokeapi_id)
