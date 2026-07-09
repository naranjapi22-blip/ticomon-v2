from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.evolution.evolution_cost_policy import EvolutionCostPolicy
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.evolution.evolution_result import EvolutionResult
from core.evolution.evolution_rule import EvolutionRule


class EvolutionPolicy:
    """
    Domain expert responsible for validating creature evolutions.
    """

    def __init__(
        self,
        cost_policy: EvolutionCostPolicy,
    ) -> None:
        self._cost_policy = cost_policy

    def validate(
        self,
        creature: Creature,
        inventory: CandyInventory,
        rule: EvolutionRule,
    ) -> EvolutionResult:
        """
        Validates whether a creature can evolve.
        """

        cost = self._cost_policy.calculate(
            candy_type=rule.candy_type,
            tier=rule.tier,
        )

        bundle = CandyBundle.from_amounts(
            cost,
        )

        if not inventory.has(bundle):
            return EvolutionResult.failed(
                previous_species=creature.species,
                reason=EvolutionFailureReason.NOT_ENOUGH_CANDIES,
            )

        return EvolutionResult(
            success=True,
            previous_species=creature.species,
            evolved_species=None,
            consumed_candies=bundle,
        )

    def get_cost(
        self,
        rule: EvolutionRule,
    ) -> CandyAmount:
        return self._cost_policy.calculate(
            candy_type=rule.candy_type,
            tier=rule.tier,
        )
