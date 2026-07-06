from core.evolution.evolution_stage import EvolutionStage
from core.spawn.spawn_rarity import SpawnRarity


class SpawnRarityClassifier:

    def classify(
        self,
        *,
        capture_rate: int,
        base_stat_total: int,
        is_legendary: bool,
        is_mythical: bool,
        evolution_stage: EvolutionStage,
    ) -> SpawnRarity:

        if is_mythical:
            return SpawnRarity.MYTHICAL

        if is_legendary:
            return SpawnRarity.LEGENDARY

        if evolution_stage == EvolutionStage.FINAL:

            if base_stat_total >= 520:
                return SpawnRarity.EPIC

            return SpawnRarity.VERY_RARE

        if evolution_stage == EvolutionStage.SECOND:

            if capture_rate <= 45:
                return SpawnRarity.VERY_RARE

            return SpawnRarity.UNCOMMON

        # FIRST

        if capture_rate >= 200:
            return SpawnRarity.VERY_COMMON

        if capture_rate >= 150:
            return SpawnRarity.COMMON

        if capture_rate >= 100:
            return SpawnRarity.UNCOMMON

        if capture_rate >= 45:
            return SpawnRarity.RARE

        return SpawnRarity.VERY_RARE
