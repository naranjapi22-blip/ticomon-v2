from __future__ import annotations

import asyncio
import io

import discord
from PIL import Image

from application.battle.exceptions import BattleNotFound
from application.bootstrap.core import CoreServices
from core.battle.engine.battle_step import BattleStep, BattleStepType
from interfaces.discord.battle.trainer_display import resolve_trainer_display_name

_TRANSIENT_DISCORD_STATUSES = frozenset({429, 502, 503, 504})
_MAX_MESSAGE_EDIT_RETRIES = 4


class BattleArenaView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        battle_id: int,
        initiator_id: int,
        opponent_id: int,
    ) -> None:
        super().__init__(timeout=300)
        self.core = core
        self.battle_id = battle_id
        self.initiator_id = initiator_id
        self.opponent_id = opponent_id
        self.message: discord.Message | None = None
        self._side_a_name = f"Trainer {initiator_id}"
        self._side_b_name = f"Trainer {opponent_id}"
        self._side_a_meta: list[tuple[int, bool]] = []
        self._side_b_meta: list[tuple[int, bool]] = []
        self._last_gif_bytes: bytes | None = None
        self._battle_background: Image.Image | None = None
        self._side_a_sprite: tuple[int, bool] | None = None
        self._side_b_sprite: tuple[int, bool] | None = None

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id not in {self.initiator_id, self.opponent_id}:
            await interaction.response.send_message(
                "❌ You are not part of this battle.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

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
        await interaction.response.defer()

        try:
            battle = await self.core.battle_application_service.get_battle(
                self.battle_id,
            )
        except BattleNotFound as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)
            return

        if not battle.is_ready:
            await interaction.followup.send(
                "❌ Both trainers must pick their teams first.",
                ephemeral=True,
            )
            return

        await self._load_fighter_metadata()

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

        renderer = self.core.battle_renderer
        self._battle_background = renderer.get_background_for_battle(
            self.battle_id,
        )

        try:
            result = await self.core.battle_execution_service.run_battle(
                self.battle_id,
                initiator_display_name=self._side_a_name,
                opponent_display_name=self._side_b_name,
            )
        except Exception as error:
            await interaction.followup.send(
                f"❌ Battle failed: {error}",
                ephemeral=True,
            )
            return

        for child in self.children:
            child.disabled = True

        turn_number = 0
        replay_service = self.core.battle_replay_service

        async def on_step(step: BattleStep, recent_lines: tuple[str, ...]) -> None:
            nonlocal turn_number

            if step.step_type is BattleStepType.START:
                turn_number = 1
            elif step.step_type is BattleStepType.ATTACK:
                turn_number += 1

            if replay_service.should_update_sprite_cache(step):
                self._side_a_sprite = self._pokeapi_for_side(self._side_a_name, step)
                self._side_b_sprite = self._pokeapi_for_side(self._side_b_name, step)

            image_updated = False
            if replay_service.should_update_hp_image(step):
                side_a_sprite = self._side_a_sprite or self._pokeapi_for_side(
                    self._side_a_name,
                    step,
                )
                side_b_sprite = self._side_b_sprite or self._pokeapi_for_side(
                    self._side_b_name,
                    step,
                )
                frame = self.core.battle_display_service.frame_from_step(
                    step,
                    side_a_pokeapi_id=side_a_sprite[0],
                    side_b_pokeapi_id=side_b_sprite[0],
                    side_a_shiny=side_a_sprite[1],
                    side_b_shiny=side_b_sprite[1],
                    turn_number=turn_number,
                    side_a_display_name=self._side_a_name,
                    side_b_display_name=self._side_b_name,
                )
                self._last_gif_bytes = renderer.render_to_bytes(
                    frame,
                    background=self._battle_background,
                )
                image_updated = True

            embed = discord.Embed(
                title="⚔️ Battle Arena",
                description="\n".join(recent_lines),
                color=discord.Color.gold(),
            )

            if self.message is None:
                return

            attachments = None
            if self._last_gif_bytes is not None:
                embed.set_image(url="attachment://battle.gif")
                if image_updated:
                    attachments = [
                        discord.File(
                            io.BytesIO(self._last_gif_bytes),
                            filename="battle.gif",
                        )
                    ]
                elif self.message.attachments:
                    attachments = list(self.message.attachments)

            await self._edit_replay_message(embed=embed, attachments=attachments)

        await replay_service.replay(result.steps, on_step)

        winner_text = (
            f"{self._side_a_name} wins!"
            if result.winner_trainer_id == self.initiator_id
            else (
                f"{self._side_b_name} wins!"
                if result.winner_trainer_id == self.opponent_id
                else f"{result.winner_side_name} wins!"
            )
        )
        if self.message is not None:
            final_embed = discord.Embed(
                title="🏆 Battle Complete",
                description=winner_text,
                color=discord.Color.gold(),
            )
            if self._last_gif_bytes is not None:
                final_embed.set_image(url="attachment://battle.gif")
                await self._edit_replay_message(
                    embed=final_embed,
                    attachments=[
                        discord.File(
                            io.BytesIO(self._last_gif_bytes),
                            filename="battle.gif",
                        )
                    ],
                )
            else:
                await self._edit_replay_message(embed=final_embed)

    def build_embed(self, battle) -> discord.Embed:
        initiator_status = (
            "✅ Ready" if battle.has_party(self.initiator_id) else "⏳ Picking"
        )
        opponent_status = (
            "✅ Ready" if battle.has_party(self.opponent_id) else "⏳ Picking"
        )

        return (
            discord.Embed(
                title="⚔️ Battle Ready",
                description="Both teams are locked. Press **Start Battle** when ready.",
                color=discord.Color.orange(),
            )
            .add_field(
                name="Initiator",
                value=f"<@{self.initiator_id}> — {initiator_status}",
                inline=False,
            )
            .add_field(
                name="Opponent",
                value=f"<@{self.opponent_id}> — {opponent_status}",
                inline=False,
            )
        )

    async def _load_fighter_metadata(self) -> None:
        initiator_ids = (
            await self.core.battle_application_service.get_party_creature_ids(
                self.battle_id,
                self.initiator_id,
            )
        )
        opponent_ids = (
            await self.core.battle_application_service.get_party_creature_ids(
                self.battle_id,
                self.opponent_id,
            )
        )

        initiator_creatures = await self.core.creature_repository.get_many(
            list(initiator_ids),
        )
        opponent_creatures = await self.core.creature_repository.get_many(
            list(opponent_ids),
        )

        creatures_by_id = {
            creature.id: creature
            for creature in initiator_creatures + opponent_creatures
        }

        self._side_a_meta = [
            (
                creatures_by_id[creature_id].species.pokeapi_id,
                creatures_by_id[creature_id].is_shiny,
            )
            for creature_id in initiator_ids
        ]
        self._side_b_meta = [
            (
                creatures_by_id[creature_id].species.pokeapi_id,
                creatures_by_id[creature_id].is_shiny,
            )
            for creature_id in opponent_ids
        ]

    def _pokeapi_for_side(
        self,
        side_name: str,
        step: BattleStep,
    ) -> tuple[int, bool]:
        side_state = step.state_snapshot.get(side_name, {})
        active_index = side_state.get("active_index", 0)

        if side_name == self._side_a_name:
            meta = self._side_a_meta
        elif side_name == self._side_b_name:
            meta = self._side_b_meta
        else:
            meta = self._side_a_meta

        if not meta:
            return 25, False

        index = min(active_index, len(meta) - 1)
        return meta[index]

    async def _edit_replay_message(
        self,
        *,
        embed: discord.Embed,
        attachments: list[discord.File] | None = None,
    ) -> None:
        if self.message is None:
            return

        for attempt in range(_MAX_MESSAGE_EDIT_RETRIES):
            try:
                edit_kwargs: dict[str, object] = {
                    "embed": embed,
                    "view": self,
                }
                if attachments is not None:
                    edit_kwargs["attachments"] = attachments
                await self.message.edit(**edit_kwargs)
                return
            except discord.HTTPException as error:
                if not _is_transient_discord_error(error) or attempt >= (
                    _MAX_MESSAGE_EDIT_RETRIES - 1
                ):
                    raise

            await asyncio.sleep(1.5 * (2**attempt))


def _is_transient_discord_error(error: discord.HTTPException) -> bool:
    if isinstance(error, discord.DiscordServerError):
        return True
    return error.status in _TRANSIENT_DISCORD_STATUSES
