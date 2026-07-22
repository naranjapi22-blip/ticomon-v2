import logging

import discord

from application.release.exceptions import ReleaseCreatureAssignedToTeam
from interfaces.discord.application_emojis import (
    candy_emoji_prefix,
    get_application_emojis,
    species_emoji_prefix,
)
from interfaces.discord.release_messages import assigned_creatures_message

logger = logging.getLogger(__name__)


class ReleaseConfirmButton(discord.ui.Button):

    def __init__(
        self,
        core,
        trainer_id: int,
        collection_numbers: list[int],
    ):
        super().__init__(
            label="✅ Confirm",
            style=discord.ButtonStyle.success,
        )

        self._core = core
        self._trainer_id = trainer_id
        self._collection_numbers = collection_numbers

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer()

        try:
            result = await self._core.release_application.release(
                trainer_id=self._trainer_id,
                collection_numbers=self._collection_numbers,
            )
        except ReleaseCreatureAssignedToTeam as error:
            self.view.stop()
            await interaction.edit_original_response(
                content=await assigned_creatures_message(
                    self._core,
                    self._trainer_id,
                    error,
                ),
                view=None,
            )
            return
        except Exception:
            self.view.stop()
            logger.exception("Unexpected error while releasing creatures")
            await interaction.edit_original_response(
                content="❌ The Pokémon could not be released. Please try again later.",
                view=None,
            )
            return

        emojis = await get_application_emojis(interaction.client)
        released = "\n".join(
            f"• {species_emoji_prefix(emojis, creature.species.pokeapi_id)}"
            f"#{creature.collection_number} {creature.species.name.title()}"
            for creature in result.released_creatures
        )
        rewards = "\n".join(
            f"• {candy_emoji_prefix(emojis, candy_type)}"
            f"{candy_type.value.title()} Candy ×{amount}"
            for candy_type, amount in result.reward_bundle.items()
        )

        await interaction.edit_original_response(
            content=(
                "## Released\n\n"
                f"{released}\n\n"
                "## Rewards\n\n"
                f"{rewards}\n\n"
                "✅ Pokémon released successfully."
            ),
            view=None,
        )
