from core.achievement.reward_policy import AchievementRewardPolicy
from core.candy.candy_type import CandyType
from test.builders.species_builder import SpeciesBuilder


def test_reward_for_single_type_species_uses_that_type() -> None:
    species = SpeciesBuilder().with_types(["fire"]).build()

    reward = AchievementRewardPolicy().reward_for(species, total_amount=4)

    assert reward.get(CandyType.FIRE) == 4


def test_reward_for_dual_type_species_splits_like_capture_rewards() -> None:
    species = SpeciesBuilder().with_types(["fire", "flying"]).build()

    reward = AchievementRewardPolicy().reward_for(species, total_amount=6)

    assert reward.get(CandyType.FIRE) == 3
    assert reward.get(CandyType.FLYING) == 3
