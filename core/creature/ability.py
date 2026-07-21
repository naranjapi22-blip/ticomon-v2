from __future__ import annotations

from dataclasses import dataclass


def canonicalize_ability_id(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("'", "")


@dataclass(frozen=True)
class Ability:
    id: str
    display_name: str
    slot: int = 1
    is_hidden: bool = False
    effect: str | None = None


class AbilityCatalog:
    """Source of abilities available to a species or form."""

    def abilities_for(
        self, species_id: int, form_name: str | None = None
    ) -> tuple[Ability, ...]:
        raise NotImplementedError


class AbilityAssignmentPolicy:
    def __init__(self, catalog: AbilityCatalog, random_source=None) -> None:
        self._catalog = catalog
        self._random_source = random_source

    def assign_for_species(self, species_id: int, *, seed: str | None = None) -> str:
        abilities = self._catalog.abilities_for(species_id)
        if not abilities:
            raise ValueError(
                f"No ability catalog is available for species {species_id}."
            )
        if len(abilities) == 1:
            return abilities[0].id
        if self._random_source is not None:
            return self._random_source.choice(abilities).id
        import hashlib

        digest = hashlib.sha256(f"{seed or species_id}:{species_id}".encode()).digest()
        return abilities[int.from_bytes(digest[:8], "big") % len(abilities)].id
