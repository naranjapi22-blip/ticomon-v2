from dataclasses import dataclass


@dataclass(frozen=True)
class Variant:
    """
    Representa una variante estética disponible para una Species.

    Una Variant no modifica las reglas del juego; únicamente describe
    una apariencia que una Creature puede tener.
    """

    id: int
    name: str