from __future__ import annotations

import asyncio
import io
import logging
import tempfile
from pathlib import Path

import discord

from application.battle.exceptions import BattleNotFound
from interfaces.discord.battle.trainer_display import resolve_trainer_display_name
from interfaces.discord.views.battle_arena_view import BattleArenaView
from rendering.battle.video_renderer import render_battle_video

logger = logging.getLogger(__name__)


class BattleVideoArenaView(BattleArenaView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._started = False

    @discord.ui.button(
        label="Start Battle",
        style=discord.ButtonStyle.danger,
        emoji="⚔️",
    )
    async def start_battle(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self._started:
            return
        self._started = True

        await interaction.response.defer()

        try:
            battle = await self.core.battle_application_service.get_battle(
                self.battle_id,
            )
        except BattleNotFound as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)
            return

        if not battle.is_ready:
            self._started = False
            await interaction.followup.send(
                "❌ Both trainers must pick their teams first.",
                ephemeral=True,
            )
            return

        self._side_a_name = await resolve_trainer_display_name(
            interaction.client,
            interaction.guild,
            self.initiator_id,
        )
        self._side_b_name = await resolve_trainer_display_name(
            interaction.client,
            interaction.guild,
            self.opponent_id,
        )
        await self._load_fighter_metadata()
        background = self.core.battle_renderer.get_background_for_battle(
            self.battle_id,
        )

        for child in self.children:
            child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)

        try:
            result = await self.core.battle_execution_service.run_battle(
                self.battle_id,
                initiator_display_name=self._side_a_name,
                opponent_display_name=self._side_b_name,
            )
            with tempfile.TemporaryDirectory(prefix="ticomon_battle_") as directory:
                output_path = Path(directory) / "battle.mp4"
                metadata = {
                    self._side_a_name: tuple(self._side_a_meta),
                    self._side_b_name: tuple(self._side_b_meta),
                }
                await asyncio.to_thread(
                    render_battle_video,
                    result,
                    metadata,
                    self._side_a_name,
                    self._side_b_name,
                    background,
                    output_path,
                )
                if self.message is not None:
                    video_file = discord.File(
                        io.BytesIO(output_path.read_bytes()),
                        filename="battle.mp4",
                    )
                    await self.message.edit(
                        embed=discord.Embed(
                            title="🏆 Battle Complete",
                            description=(f"{result.winner_side_name} wins!"),
                            color=discord.Color.gold(),
                        ),
                        view=self,
                        attachments=[video_file],
                    )
        except Exception:
            logger.exception("Experimental battle video failed")
            await interaction.followup.send(
                "⚠️ Battle finished, but the video could not be generated.",
                ephemeral=True,
            )
