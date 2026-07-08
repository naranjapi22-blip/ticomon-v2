from dataclasses import dataclass


@dataclass(slots=True)
class PokedexFilter:
    discovered: bool | None = None
    pokemon_type: str | None = None
    generation: int | None = None
    legendary: bool = False
    mythical: bool = False
    shiny: bool = False
