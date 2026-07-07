import discord


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
        from interfaces.discord.views.capture_view import CaptureView

        result = await self._core.capture_application.capture(
            trainer_id=interaction.user.id,
        )

        if result.success:
            await interaction.response.edit_message(
                content=f"✅ You captured {result.creature.species.name}!",
                view=None,
            )
        else:
            await interaction.response.edit_message(
                content=(
                    f"🎯 You threw a "
                    f"{result.attempt.capture_ball.name}\n"
                    f"Chance: {result.attempt.chance:.2f}%\n\n"
                    "❌ Capture failed!"
                ),
                view=CaptureView(self._core),
            )
