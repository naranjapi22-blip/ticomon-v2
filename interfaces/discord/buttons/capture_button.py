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

        ball_name = result.attempt.capture_ball.name.replace(
            "_",
            " ",
        ).title()

        if result.success:

            trainer = await self._core.profile_service.get_selected_trainer(
                interaction.user.id,
            )

            sprite_path = get_capture_sprite(
                species_id=result.creature.species.id,
                shiny=result.creature.is_shiny,
            )

            animation = CaptureAnimation(
                sprite_path=sprite_path,
                pokemon_name=result.creature.species.name,
                trainer=trainer.gif.removesuffix(".gif"),
                pokeball=result.attempt.capture_ball.name,
                capturado=True,
                tipo=result.creature.species.types[0],
            )

            gif = await asyncio.to_thread(
                animation.gif_bytes,
            )

            rewards = "\n".join(
                f"🍬 {candy_type.value.title()}: +{amount}"
                for candy_type, amount in result.reward.items()
            )

            await interaction.response.edit_message(
                content=(
                    f"🎉 {interaction.user.mention} caught "
                    f"{result.creature.species.name.title()} "
                    f"using a {ball_name}!\n"
                    f"🎯 Capture Chance: {result.attempt.chance * 100:.2f}%\n\n"
                    f"{rewards}"
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
