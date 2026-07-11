class IVRating:
    MAX_TOTAL = 186

    @staticmethod
    def percentage(ivs) -> int:
        total = (
            ivs.hp
            + ivs.attack
            + ivs.defense
            + ivs.special_attack
            + ivs.special_defense
            + ivs.speed
        )

        return round((total / IVRating.MAX_TOTAL) * 100)
