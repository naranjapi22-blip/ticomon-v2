from dataclasses import dataclass

from core.species.species import Species


@dataclass(frozen=True)
class PokedexEntryDTO:
    species: Species
    discovered: bool


@dataclass(frozen=True)
class PokedexDTO:
    entries: tuple[PokedexEntryDTO, ...]
