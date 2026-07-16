from core.collection.catalog import (
    ALCREMIE_ENTRIES,
    COLLECTIONS,
    FLABEBE_ENTRIES,
    FOSSIL_ENTRIES,
    FURFROU_ENTRIES,
    TECHNOLOGY_ENTRIES,
    VIVILLON_ENTRIES,
    CollectionId,
)
from core.shop.catalog import ALCREMIE_CREAMS, ALCREMIE_DECORATIONS


def test_collection_catalogues_have_the_exact_supported_entries():
    assert len(FOSSIL_ENTRIES) == 15
    assert len(TECHNOLOGY_ENTRIES) == 6
    assert len(ALCREMIE_ENTRIES) == 45
    assert len(VIVILLON_ENTRIES) == 17
    assert len(FURFROU_ENTRIES) == 10
    assert len(FLABEBE_ENTRIES) == 12
    assert len(COLLECTIONS) == 6


def test_collection_catalogues_exclude_unsupported_variants():
    technology_variants = {entry.variant_name for entry in TECHNOLOGY_ENTRIES}
    assert "frost" not in technology_variants
    assert "fan" not in technology_variants
    assert "eternal" not in {entry.variant_name for entry in FLABEBE_ENTRIES}
    assert "pokeball" not in {entry.variant_name for entry in VIVILLON_ENTRIES}
    assert "fancy" not in {entry.variant_name for entry in VIVILLON_ENTRIES}


def test_alcremie_collection_is_the_canonical_9_by_5_catalogue():
    expected = {
        f"{cream}-{decoration}"
        for cream in ALCREMIE_CREAMS
        for decoration in ALCREMIE_DECORATIONS
    }
    assert {entry.variant_name for entry in ALCREMIE_ENTRIES} == expected
    assert len({entry.variant_name for entry in ALCREMIE_ENTRIES}) == 45


def test_collection_mint_rewards_match_the_defined_completion_rewards():
    rewards = {
        definition.id: [milestone.mints for milestone in definition.milestones]
        for definition in COLLECTIONS
    }
    assert rewards[CollectionId.FOSSIL_RESTORATION] == [0, 0, 1]
    assert rewards[CollectionId.ALCREMIE] == [0, 0, 1, 2]
