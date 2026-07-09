import discord

from core.evolution.evolution_rule import EvolutionRule
from interfaces.discord.evolution_sender import (
    edit_evolution_result,
)


class EvolutionConfirmButton(discord.ui.Button):

    def __init__(
        self,
        core,
        trainer_id: int,
        collection_number: int,
        rule: EvolutionRule,
    ):
        super().__init__(
            label="✅ Evolve",
            style=discord.ButtonStyle.success,
        )

        self._core = core
        self._trainer_id = trainer_id
        self._collection_number = collection_number
        self._rule = rule

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        result = await self._core.evolution_application.evolve(
            trainer_id=self._trainer_id,
            collection_number=self._collection_number,
            rule=self._rule,
        )

        if not result.success:

            await interaction.response.edit_message(
                content="❌ Evolution failed.",
                view=None,
            )

            return

        await edit_evolution_result(
            interaction=interaction,
            result=result,
        )
