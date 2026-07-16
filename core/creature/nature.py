from dataclasses import dataclass

from core.creature.stat import Stat

_MODIFIERS = {
    "hardy": {},
    "lonely": {Stat.ATTACK: 1.1, Stat.DEFENSE: 0.9},
    "brave": {Stat.ATTACK: 1.1, Stat.SPEED: 0.9},
    "adamant": {Stat.ATTACK: 1.1, Stat.SP_ATTACK: 0.9},
    "naughty": {Stat.ATTACK: 1.1, Stat.SP_DEFENSE: 0.9},
    "bold": {Stat.DEFENSE: 1.1, Stat.ATTACK: 0.9},
    "docile": {},
    "relaxed": {Stat.DEFENSE: 1.1, Stat.SPEED: 0.9},
    "impish": {Stat.DEFENSE: 1.1, Stat.SP_ATTACK: 0.9},
    "lax": {Stat.DEFENSE: 1.1, Stat.SP_DEFENSE: 0.9},
    "timid": {Stat.SPEED: 1.1, Stat.ATTACK: 0.9},
    "hasty": {Stat.SPEED: 1.1, Stat.DEFENSE: 0.9},
    "serious": {},
    "jolly": {Stat.SPEED: 1.1, Stat.SP_ATTACK: 0.9},
    "naive": {Stat.SPEED: 1.1, Stat.SP_DEFENSE: 0.9},
    "modest": {Stat.SP_ATTACK: 1.1, Stat.ATTACK: 0.9},
    "mild": {Stat.SP_ATTACK: 1.1, Stat.DEFENSE: 0.9},
    "quiet": {Stat.SP_ATTACK: 1.1, Stat.SPEED: 0.9},
    "bashful": {},
    "rash": {Stat.SP_ATTACK: 1.1, Stat.SP_DEFENSE: 0.9},
    "calm": {Stat.SP_DEFENSE: 1.1, Stat.ATTACK: 0.9},
    "gentle": {Stat.SP_DEFENSE: 1.1, Stat.DEFENSE: 0.9},
    "sassy": {Stat.SP_DEFENSE: 1.1, Stat.SPEED: 0.9},
    "careful": {Stat.SP_DEFENSE: 1.1, Stat.SP_ATTACK: 0.9},
    "quirky": {},
}


@dataclass(frozen=True)
class Nature:
    name: str

    def __post_init__(self):
        if self.name not in _MODIFIERS:
            raise ValueError(f"Unknown nature: {self.name}")

    def modifier_for(
        self,
        stat: Stat,
    ) -> float:
        return _MODIFIERS[self.name].get(
            stat,
            1.0,
        )

    @classmethod
    def from_effect(
        cls,
        increased: Stat,
        decreased: Stat,
    ) -> "Nature":
        if Stat.HP in {increased, decreased}:
            raise ValueError("HP cannot be modified by a Nature Mint.")
        if increased is decreased:
            raise ValueError("A nature cannot increase and decrease the same stat.")

        for name, modifiers in _MODIFIERS.items():
            if modifiers.get(increased) == 1.1 and modifiers.get(decreased) == 0.9:
                return cls(name)

        raise ValueError("The stat combination does not match an official nature.")

    def effect(self) -> tuple[Stat | None, Stat | None]:
        modifiers = _MODIFIERS[self.name]
        increased = next(
            (stat for stat, value in modifiers.items() if value == 1.1),
            None,
        )
        decreased = next(
            (stat for stat, value in modifiers.items() if value == 0.9),
            None,
        )
        return increased, decreased

    def arrow_for(
        self,
        stat: Stat,
    ) -> str:
        modifier = self.modifier_for(stat)

        if modifier > 1:
            return " ⬆️"

        if modifier < 1:
            return " ⬇️"

        return ""

    def __str__(self) -> str:
        return self.name.title()
