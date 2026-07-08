from dataclasses import dataclass


@dataclass(frozen=True)
class Size:
    value: float

    def __post_init__(self):
        if not 0.5 <= self.value <= 1.5:
            raise ValueError("Size must be between 0.5 and 1.5")

    @property
    def category(self) -> str:
        if self.value < 0.60:
            return "XXS"

        if self.value < 0.75:
            return "XS"

        if self.value < 0.90:
            return "S"

        if self.value < 1.10:
            return "M"

        if self.value < 1.25:
            return "L"

        if self.value < 1.40:
            return "XL"

        return "XXL 👑"

    def __str__(self) -> str:
        return f"{self.category} " f"({self.value:.2f}×)"
