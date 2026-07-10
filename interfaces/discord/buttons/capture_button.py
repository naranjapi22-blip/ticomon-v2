import asyncio
from time import perf_counter

import discord

from core.spawn.exceptions import NoActiveSpawnSession
from rendering.animacion_captura import CaptureAnimation
from rendering.sprites import get_capture_sprite


class CaptureButton(discord.ui.Button):
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

        start = perf_counter()

        animation = CaptureAnimation(
            sprite_path=sprite_path,
            pokemon_name=result.creature.species.name,
            trainer=trainer.gif.removesuffix(".gif"),
            pokeball=result.attempt.capture_ball.name,
            capturado=True,
            tipo=result.creature.species.types[0],
        )

        print(f"[PERF] Create CaptureAnimation: " f"{perf_counter() - start:.3f}s")

        start = perf_counter()

        gif = await asyncio.to_thread(
            animation.gif_bytes,
        )

        print(f"[PERF] Generate GIF: " f"{perf_counter() - start:.3f}s")

        rewards = "\n".join(
            f"🍬 {candy_type.value.title()}: +{amount}"
            for candy_type, amount in result.reward.items()
        )

        await interaction.followup.send(
            content=(
                f"🎉 {interaction.user.mention} caught "
                f"{result.creature.species.name.title()} "
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
