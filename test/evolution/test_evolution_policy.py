from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.evolution.evolution_cost_policy import EvolutionCostPolicy
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.evolution.evolution_policy import EvolutionPolicy
from test.builders.creature_builder import CreatureBuilder
from test.builders.evolution_rule_builder import EvolutionRuleBuilder


def make_policy():

    return EvolutionPolicy(
        cost_policy=EvolutionCostPolicy(),
    )


def test_validate_success():

    creature = CreatureBuilder().build()

    rule = (
        EvolutionRuleBuilder()
        .with_candy_type(
            CandyType.FIRE,
        )
        .with_tier(
            "basic",
        )
        .build()
    )

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                10,
            )
        )
    )

    result = make_policy().validate(
        creature,
        inventory,
        rule,
    )

    assert result.success
    assert result.failure_reason is None
    assert (
        result.consumed_candies.get(
            CandyType.FIRE,
        )
        == 10
    )


def test_validate_fails_when_trainer_has_not_enough_candies():

    creature = CreatureBuilder().build()

    rule = (
        EvolutionRuleBuilder()
        .with_candy_type(
            CandyType.FIRE,
        )
        .with_tier(
            "basic",
        )
        .build()
    )

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                5,
            )
        )
    )

    result = make_policy().validate(
        creature,
        inventory,
        rule,
    )

    assert not result.success
    assert result.failure_reason == EvolutionFailureReason.NOT_ENOUGH_CANDIES


def test_validate_requires_evolution_rule():

    creature = CreatureBuilder().build()

    rule = (
        EvolutionRuleBuilder()
        .with_candy_type(
            CandyType.FIRE,
        )
        .with_tier(
            "exceptional",
        )
        .build()
    )

    inventory = CandyInventory()

    result = make_policy().validate(
        creature,
        inventory,
        rule,
    )

    assert not result.success
