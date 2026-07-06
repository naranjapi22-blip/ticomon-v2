from dataclasses import dataclass


@dataclass(frozen=True)
class SpeciesMetadata:
    """
    Información descriptiva de una especie utilizada por
    las reglas del juego.

    No representa estadísticas ni comportamiento de la especie.
    """

    generation: int
    is_baby: bool
    is_legendary: bool
    is_mythical: bool
