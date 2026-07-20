from __future__ import annotations

import discord

from core.pvp.session import PvpPhase


class PvpChallengeView(discord.ui.View):
    def __init__(self, core, session, opponent_id: int) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.session_id = session.id
        self.opponent_id = opponent_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Only the challenged trainer can answer this PvP challenge.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button) -> None:
        try:
            session = self.core.pvp_application_service.registry.get(self.session_id)
        except ValueError:
            await interaction.response.send_message(
                "This PvP challenge is no longer active.", ephemeral=True
            )
            return
        session.phase = PvpPhase.CANCELLED
        button.disabled = True
        for child in self.children:
            child.disabled = True
        self.core.pvp_application_service.cleanup(self.session_id)
        await interaction.response.edit_message(
            content=(
                "PvP challenge accepted, but the interactive PvP flow is not "
                "available yet. No battle was started."
            ),
            view=self,
        )

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button) -> None:
        self.core.pvp_application_service.decline(self.session_id)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="PvP challenge declined.",
            view=self,
        )

    async def on_timeout(self) -> None:
        self.core.pvp_application_service.cleanup(self.session_id)
        for child in self.children:
            child.disabled = True
