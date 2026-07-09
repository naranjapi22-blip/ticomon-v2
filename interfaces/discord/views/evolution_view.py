import discord

from core.evolution.evolution_rule import EvolutionRule
from interfaces.discord.buttons.evolution_button import (
    EvolutionButton,
)


class EvolutionView(discord.ui.View):

    def __init__(
        self,
        core,
        trainer_id: int,
        collection_number: int,
        options: list[EvolutionRule],
    ):
        super().__init__(
            timeout=60,
        )

        self._core = core
        self._trainer_id = trainer_id
        self._collection_number = collection_number
        self._options = options

    async def build(self):

        for rule in self._options:

            species = await self._core.species_repository.get(
                rule.to_species_id,
            )

            self.add_item(
                EvolutionButton(
                    core=self._core,
                    trainer_id=self._trainer_id,
                    collection_number=self._collection_number,
                    rule=rule,
                    species_name=species.name,
                )
            )

        return self
