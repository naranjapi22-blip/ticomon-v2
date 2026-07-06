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

    def modifier_for(self, stat: Stat) -> float:
        return _MODIFIERS[self.name].get(stat, 1.0)
