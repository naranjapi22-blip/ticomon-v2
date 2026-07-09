from core.rarity import Rarity


class SpawnRarityClassifier:

    def classify(
        self,
        *,
        capture_rate: int,
        base_stat_total: int,
        is_legendary: bool,
        is_mythical: bool,
        stage: int,
    ) -> Rarity:

        if is_mythical:
            return Rarity.MYTHICAL

        if is_legendary:
            return Rarity.LEGENDARY

        if stage == 3:

            if base_stat_total >= 520:
                return Rarity.EPIC

            return Rarity.VERY_RARE

        if stage == 2:

            if capture_rate <= 45:
                return Rarity.VERY_RARE

            return Rarity.UNCOMMON

        # Stage 1

        if capture_rate >= 200:
            return Rarity.VERY_COMMON

        if capture_rate >= 150:
            return Rarity.COMMON

        if capture_rate >= 100:
            return Rarity.UNCOMMON

        if capture_rate >= 45:
            return Rarity.RARE

        return Rarity.VERY_RARE
