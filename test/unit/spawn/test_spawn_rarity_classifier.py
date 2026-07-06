from core.evolution.evolution_stage import EvolutionStage
from core.spawn.spawn_rarity import SpawnRarity
from core.spawn.spawn_rarity_classifier import SpawnRarityClassifier


def test_mythical_is_always_mythical():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=3,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=False,
        is_mythical=True,
    )

    assert rarity == SpawnRarity.MYTHICAL


def test_legendary_is_always_legendary():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=3,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=True,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.LEGENDARY


def test_final_evolution_with_high_bst_is_epic():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=45,
        base_stat_total=600,
        evolution_stage=EvolutionStage.FINAL,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.EPIC


def test_final_evolution_with_low_bst_is_very_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=75,
        base_stat_total=450,
        evolution_stage=EvolutionStage.FINAL,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.VERY_RARE


def test_second_evolution_with_low_capture_rate_is_very_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=45,
        base_stat_total=300,
        evolution_stage=EvolutionStage.SECOND,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.VERY_RARE


def test_second_evolution_with_high_capture_rate_is_uncommon():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=120,
        base_stat_total=300,
        evolution_stage=EvolutionStage.SECOND,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.UNCOMMON


def test_first_evolution_with_very_high_capture_rate_is_very_common():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=255,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.VERY_COMMON


def test_first_evolution_with_high_capture_rate_is_common():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=180,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.COMMON


def test_first_evolution_with_medium_capture_rate_is_uncommon():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=120,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.UNCOMMON


def test_first_evolution_with_low_capture_rate_is_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=90,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.RARE


def test_first_evolution_with_very_low_capture_rate_is_very_rare():
    classifier = SpawnRarityClassifier()

    rarity = classifier.classify(
        capture_rate=3,
        base_stat_total=300,
        evolution_stage=EvolutionStage.FIRST,
        is_legendary=False,
        is_mythical=False,
    )

    assert rarity == SpawnRarity.VERY_RARE
