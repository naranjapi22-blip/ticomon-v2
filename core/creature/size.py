from dataclasses import dataclass


@dataclass(frozen=True)
class Size:
    value: float

    def __post_init__(self):
        if not 0.5 <= self.value <= 1.5:
            raise ValueError("Size must be between 0.5 and 1.5")