from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.creature.creature import Creature
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.evolution.evolution_result import EvolutionResult


class EvolutionPolicy:
    """
    Domain expert responsible for validating creature evolutions.
    """

    def validate(
        self,
        creature: Creature,
        inventory: CandyInventory,
    ) -> EvolutionResult:
        """
        Validates whether a creature can evolve.
        """

        chain = creature.species.evolution_chain

        if chain is None:
            return EvolutionResult.failed(
                previous_species=creature.species,
                reason=EvolutionFailureReason.FINAL_STAGE,
            )

        if chain.is_final_stage(
            creature.species.id,
        ):
            return EvolutionResult.failed(
                previous_species=creature.species,
                reason=EvolutionFailureReason.FINAL_STAGE,
            )

        cost = chain.candy_cost_for(
            creature.species.id,
        )

        bundle = CandyBundle.from_amounts(
            CandyAmount(
                CandyType(creature.species.types[0]),
                cost,
            )
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
