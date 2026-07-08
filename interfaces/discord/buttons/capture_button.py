import asyncio

import discord

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
        result = await self._core.capture_application.capture(
            trainer_id=interaction.user.id,
            guild_id=interaction.guild.id,
        )

        ball_name = result.attempt.capture_ball.name.replace("_", " ").title()

        if result.success:
            sprite_path = get_capture_sprite(
                species_id=result.creature.species.id,
                shiny=result.creature.is_shiny,
            )

            animation = CaptureAnimation(
                sprite_path=sprite_path,
                pokemon_name=result.creature.species.name,
                pokeball=result.attempt.capture_ball.name,
                capturado=True,
                tipo=result.creature.species.types[0],
            )

            gif = await asyncio.to_thread(
                animation.gif_bytes,
            )

            await interaction.response.edit_message(
                content=(
                    f"🎉 {interaction.user.mention} caught "
                    f"{result.creature.species.name.title()} "
                    f"using a {ball_name}!\n"
                    f"🎯 Capture Chance: {result.attempt.chance * 100:.2f}%"
                ),
                embeds=[],
                attachments=[
                    discord.File(
                        gif,
                        filename="capture.gif",
                    )
                ],
                view=None,
            )

        else:
            await interaction.response.send_message(
                (
                    f"🎯 You threw a {ball_name}\n"
                    f"Chance: {result.attempt.chance * 100:.2f}%\n\n"
                    "❌ Capture failed!"
                ),
                ephemeral=True,
            )
