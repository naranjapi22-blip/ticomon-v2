import logging

import discord

from core.evolution.evolution_rule import EvolutionRule
from interfaces.discord.evolution_sender import edit_evolution_result

logger = logging.getLogger(__name__)


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

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not view.begin_processing():
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Evolution is already being processed.",
                    ephemeral=True,
                )
            return

        await interaction.response.defer()

        try:
            result = await self._core.evolution_application.evolve(
                trainer_id=self._trainer_id,
                collection_number=self._collection_number,
                rule=self._rule,
            )
        except ValueError:
            await interaction.edit_original_response(
                content="❌ Evolution failed.",
                view=None,
            )
            return
        except Exception:
            logger.exception(
                "evolution confirmation failed trainer_id=%s",
                self._trainer_id,
            )
            await interaction.edit_original_response(
                content="❌ Evolution failed. Please try again later.",
                view=None,
            )
            return

        if not result.success:
            await interaction.edit_original_response(
                content="❌ Evolution failed.",
                view=None,
            )
            return

        await edit_evolution_result(
            interaction=interaction,
            result=result,
        )
