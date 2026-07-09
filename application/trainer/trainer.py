from dataclasses import dataclass


@dataclass(frozen=True)
class Trainer:
    id: int
    name: str
    png: str
    gif: str
