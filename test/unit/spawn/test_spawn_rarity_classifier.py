from core.rarity import Rarity
from core.spawn.spawn_rarity_classifier import SpawnRarityClassifier


def test_mythical_is_always_mythical():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=3,
        base_stat_total=300,
        stage=1,
        is_legendary=False,
        is_mythical=True,
    )

    assert rarity == Rarity.MYTHICAL


def test_legendary_is_always_legendary():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=3,
        base_stat_total=300,
        stage=1,
        is_legendary=True,
        is_mythical=False,
    )

    assert rarity == Rarity.LEGENDARY


def test_final_evolution_with_high_bst_is_epic():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=45,
        base_stat_total=600,
        stage=3,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.EPIC


def test_final_evolution_with_low_bst_is_very_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=75,
        base_stat_total=450,
        stage=3,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.VERY_RARE


def test_second_evolution_with_low_capture_rate_is_very_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=45,
        base_stat_total=300,
        stage=2,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.VERY_RARE


def test_second_evolution_with_high_capture_rate_is_uncommon():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=120,
        base_stat_total=300,
        stage=2,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.UNCOMMON


def test_first_evolution_with_very_high_capture_rate_is_very_common():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=255,
        base_stat_total=300,
        stage=1,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.VERY_COMMON


def test_first_evolution_with_high_capture_rate_is_common():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=180,
        base_stat_total=300,
        stage=1,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.COMMON


def test_first_evolution_with_medium_capture_rate_is_uncommon():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=120,
        base_stat_total=300,
        stage=1,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.UNCOMMON


def test_first_evolution_with_low_capture_rate_is_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=90,
        base_stat_total=300,
        stage=1,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.RARE


def test_first_evolution_with_very_low_capture_rate_is_very_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=3,
        base_stat_total=300,
        stage=1,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == Rarity.VERY_RARE
