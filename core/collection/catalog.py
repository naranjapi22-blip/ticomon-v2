from dataclasses import dataclass
from enum import StrEnum

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    FLABEBE_COLORS,
    FURFROU_TRIMS,
    SHOP_PRODUCTS,
    VIVILLON_PATTERNS,
    ShopStore,
    alcremie_variant_name,
)


class CollectionId(StrEnum):
    FOSSIL_RESTORATION = "fossil_restoration"
    TECHNOLOGY = "technology_collection"
    ALCREMIE = "alcremie_collection"
    VIVILLON = "vivillon_patterns"
    FURFROU = "furfrou_styles"
    FLABEBE = "flabebe_garden"


@dataclass(frozen=True, slots=True)
class CollectionEntryDefinition:
    species_name: str
    variant_name: str | None = None
    display_name: str | None = None
    shop_available: bool = False

    @property
    def label(self) -> str:
        if self.display_name is not None:
            return self.display_name
        if self.variant_name is None:
            return self.species_name.title()
        variant = self.variant_name.replace("-", " ").title()
        return f"{self.species_name.title()} ({variant})"


@dataclass(frozen=True, slots=True)
class CollectionMilestone:
    threshold: int
    candies: CandyBundle
    mints: int = 0


@dataclass(frozen=True, slots=True)
class CollectionDefinition:
    id: CollectionId
    name: str
    entries: tuple[CollectionEntryDefinition, ...]
    milestones: tuple[CollectionMilestone, ...]


@dataclass(frozen=True, slots=True)
class CollectionProgress:
    definition: CollectionDefinition
    historical_count: int
    historical_entries: frozenset[tuple[int, int | None]]
    owned_count: int
    owned_entries: frozenset[tuple[int, int | None]]

    @property
    def collected_count(self) -> int:
        """Compatibility alias for historical collection progress."""
        return self.historical_count

    @property
    def total(self) -> int:
        return len(self.definition.entries)

    @property
    def percentage(self) -> int:
        return int(self.collected_count * 100 / self.total) if self.total else 0


def _bundle(*items: tuple[CandyType, int]) -> CandyBundle:
    return CandyBundle.from_amounts(
        *(CandyAmount(kind, amount) for kind, amount in items)
    )


def _entries_for_store(store: ShopStore) -> tuple[CollectionEntryDefinition, ...]:
    return tuple(
        CollectionEntryDefinition(
            product.species_name,
            product.variant_name,
            product.display_name,
            shop_available=True,
        )
        for product in SHOP_PRODUCTS
        if product.store is store and not product.random_variant_names
    )


FOSSIL_ENTRIES = _entries_for_store(ShopStore.FOSSIL)
TECHNOLOGY_ENTRIES = _entries_for_store(ShopStore.TECHNOLOGY)
ALCREMIE_ENTRIES = tuple(
    CollectionEntryDefinition(
        "alcremie",
        alcremie_variant_name(cream, decoration),
        f"Alcremie ({cream.replace('-', ' ').title()} / {decoration.title()})",
        shop_available=True,
    )
    for cream in ALCREMIE_CREAMS
    for decoration in ALCREMIE_DECORATIONS
)
VIVILLON_ENTRIES = tuple(
    CollectionEntryDefinition(
        "vivillon",
        pattern,
        f"Vivillon ({pattern.replace('-', ' ').title()})",
        shop_available=True,
    )
    for pattern in VIVILLON_PATTERNS
)
FURFROU_ENTRIES = (
    CollectionEntryDefinition(
        "furfrou",
        display_name="Furfrou (Natural)",
        shop_available=True,
    ),
    *tuple(
        CollectionEntryDefinition(
            "furfrou",
            trim,
            f"Furfrou ({trim.replace('-', ' ').title()})",
            shop_available=True,
        )
        for trim in FURFROU_TRIMS
    ),
)
FLABEBE_ENTRIES = tuple(
    CollectionEntryDefinition(
        species_name,
        color,
        f"{species_name.title()} ({color.title()})",
        shop_available=species_name == "flabebe",
    )
    for color in FLABEBE_COLORS
    for species_name in ("flabebe", "floette", "florges")
)

_COLLECTION_ENTRY_IDENTITIES = frozenset(
    (entry.species_name, entry.variant_name)
    for entries in (
        FOSSIL_ENTRIES,
        TECHNOLOGY_ENTRIES,
        ALCREMIE_ENTRIES,
        VIVILLON_ENTRIES,
        FURFROU_ENTRIES,
        FLABEBE_ENTRIES,
    )
    for entry in entries
)
_COLLECTION_SPECIES_NAMES = frozenset(
    species_name for species_name, _ in _COLLECTION_ENTRY_IDENTITIES
)


def is_recordable_collection_identity(
    species_name: str,
    variant_name: str | None,
) -> bool:
    """Reject technical or alias forms of species covered by active albums."""
    if species_name not in _COLLECTION_SPECIES_NAMES:
        return True
    return (species_name, variant_name) in _COLLECTION_ENTRY_IDENTITIES


COLLECTIONS: tuple[CollectionDefinition, ...] = (
    CollectionDefinition(
        CollectionId.FOSSIL_RESTORATION,
        "Fossil Restoration",
        FOSSIL_ENTRIES,
        (
            CollectionMilestone(5, _bundle((CandyType.ROCK, 20))),
            CollectionMilestone(10, _bundle((CandyType.ROCK, 30))),
            CollectionMilestone(15, _bundle((CandyType.ROCK, 50)), 1),
        ),
    ),
    CollectionDefinition(
        CollectionId.TECHNOLOGY,
        "Technology Collection",
        TECHNOLOGY_ENTRIES,
        (
            CollectionMilestone(
                3, _bundle((CandyType.ELECTRIC, 20), (CandyType.NORMAL, 20))
            ),
            CollectionMilestone(
                6, _bundle((CandyType.ELECTRIC, 30), (CandyType.GHOST, 30)), 1
            ),
        ),
    ),
    CollectionDefinition(
        CollectionId.ALCREMIE,
        "Alcremie Collection",
        ALCREMIE_ENTRIES,
        (
            CollectionMilestone(5, _bundle((CandyType.FAIRY, 20))),
            CollectionMilestone(15, _bundle((CandyType.FAIRY, 40))),
            CollectionMilestone(30, _bundle((CandyType.FAIRY, 60)), 1),
            CollectionMilestone(45, _bundle((CandyType.FAIRY, 100)), 2),
        ),
    ),
    CollectionDefinition(
        CollectionId.VIVILLON,
        "Vivillon Patterns",
        VIVILLON_ENTRIES,
        (
            CollectionMilestone(
                5, _bundle((CandyType.BUG, 20), (CandyType.FLYING, 20))
            ),
            CollectionMilestone(
                10, _bundle((CandyType.BUG, 30), (CandyType.FLYING, 30))
            ),
            CollectionMilestone(
                17, _bundle((CandyType.BUG, 50), (CandyType.FLYING, 50)), 1
            ),
        ),
    ),
    CollectionDefinition(
        CollectionId.FURFROU,
        "Furfrou Styles",
        FURFROU_ENTRIES,
        (
            CollectionMilestone(5, _bundle((CandyType.NORMAL, 30))),
            CollectionMilestone(10, _bundle((CandyType.NORMAL, 60)), 1),
        ),
    ),
    CollectionDefinition(
        CollectionId.FLABEBE,
        "Flabébé Garden",
        FLABEBE_ENTRIES,
        (
            CollectionMilestone(4, _bundle((CandyType.FAIRY, 20))),
            CollectionMilestone(8, _bundle((CandyType.FAIRY, 40))),
            CollectionMilestone(12, _bundle((CandyType.FAIRY, 60)), 1),
        ),
    ),
)


def collection_by_id(collection_id: str | CollectionId) -> CollectionDefinition:
    try:
        normalized = CollectionId(collection_id)
    except ValueError as error:
        raise ValueError("Unknown collection.") from error
    for definition in COLLECTIONS:
        if definition.id is normalized:
            return definition
    raise ValueError("Unknown collection.")


def calculate_progress(
    definition: CollectionDefinition,
    resolved_entry_identities: tuple[tuple[int, int | None], ...],
    obtained_entries: frozenset[tuple[int, int | None]],
    owned_entries: frozenset[tuple[int, int | None]],
) -> CollectionProgress:
    if len(resolved_entry_identities) != len(definition.entries):
        raise ValueError("Collection entries must be resolved exactly once.")
    historical = frozenset(
        identity
        for identity in resolved_entry_identities
        if identity in obtained_entries
    )
    owned = frozenset(
        identity for identity in resolved_entry_identities if identity in owned_entries
    )
    return CollectionProgress(
        definition,
        len(historical),
        historical,
        len(owned),
        owned,
    )
