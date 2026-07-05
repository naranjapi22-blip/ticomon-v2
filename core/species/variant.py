from dataclasses import dataclass


@dataclass
class Variant:
    """
    Representa una variación estética de una Species.

    Una Variant no modifica las reglas del juego, únicamente la
    apariencia de una Species.
    """

    id: int
    name: str