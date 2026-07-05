from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionChain:
    id: int

    # especies en la cadena (IDs o Species futuras)
    species: list[int]

    # coste de evolución por especie
    candy_requirements: dict[int, int]