import asyncio
import math
from time import monotonic

import discord

from core.spawn.exceptions import NoActiveSpawnSession
from rendering.capture_animation import CaptureAnimation
from rendering.sprites import get_capture_sprite


class CaptureButton(discord.ui.Button):
    COOLDOWN_SECONDS = 10
    _last_attempt: dict[int, float] = {}

    def __init__(self, core):
        super().__init__(
            label="🎯 Capture",
            style=discord.ButtonStyle.success,
        )

        self._core = core

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        now = monotonic()

        last_attempt = self._last_attempt.get(interaction.user.id)

        if last_attempt is not None:
            remaining = self.COOLDOWN_SECONDS - (now - last_attempt)

            if remaining > 1:
                await interaction.followup.send(
                    (
                        f"⏳ Please wait "
                        f"{math.ceil(remaining)} seconds before trying again."
                    ),
                    ephemeral=True,
                )
                return

        try:
            result = await self._core.capture_application.capture(
                trainer_id=interaction.user.id,
                guild_id=interaction.guild.id,
            )
        except NoActiveSpawnSession:
            await interaction.followup.send(
                "❌ This encounter is no longer available.",
                ephemeral=True,
            )
            return

        # The attempt was valid; start the cooldown.
        self._last_attempt[interaction.user.id] = monotonic()

        ball_name = result.attempt.capture_ball.name.replace(
            "_",
            " ",
        ).title()

        if not result.success:
            await interaction.followup.send(
                content=(
                    f"❌ You failed to catch the Pokémon.\n"
                    f"🎯 Capture Chance: {result.attempt.chance * 100:.2f}%"
                ),
                ephemeral=True,
            )
            return

        trainer = await self._core.profile_service.get_selected_trainer(
            interaction.user.id,
        )

        sprite_path = get_capture_sprite(
            result.creature,
        )

        animation = CaptureAnimation(
            sprite_path=sprite_path,
            pokemon_name=result.creature.species.name,
            trainer=trainer.gif.removesuffix(".gif"),
            pokeball=result.attempt.capture_ball.name,
            captured=True,
            type_name=result.creature.species.types[0],
        )

        gif = await asyncio.to_thread(
            animation.gif_bytes,
        )

        rewards = "\n".join(
            f"🍬 {candy_type.value.title()}: +{amount}"
            for candy_type, amount in result.reward.items()
        )

        await interaction.followup.send(
            content=(
                f"🎉 {interaction.user.mention} caught "
                f"{result.creature.species.name.title()} "
                f"(#{result.creature.collection_number}) "
                f"using a {ball_name}!\n"
                f"🎯 Capture Chance: {result.attempt.chance * 100:.2f}%\n\n"
                f"{rewards}"
            ),
            file=discord.File(
                gif,
                filename="capture.gif",
            ),
        )

        await interaction.delete_original_response()
