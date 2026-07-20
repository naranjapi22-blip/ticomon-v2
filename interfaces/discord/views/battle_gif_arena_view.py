from __future__ import annotations

import asyncio
import io
import logging
import re

import discord
import requests

from core.battle.engine.battle_step import BattleStep, BattleStepType
from interfaces.discord.battle.trainer_display import resolve_trainer_display_name
from interfaces.discord.views.battle_arena_view import BattleArenaView
from rendering.battle.assets import BattleAssets
from rendering.battle.sprite_urls import (
    battle_initiator_sprite_url,
    battle_opponent_sprite_url,
)

logger = logging.getLogger(__name__)

_MOVE_MESSAGE = re.compile(r"^.+?'s (?P<pokemon>.+?) uses (?P<move>.+)!$")
_SWITCH_MESSAGE = re.compile(r"sends out (?P<pokemon>.+)!$")
_GIF_BYTES_CACHE: dict[str, bytes] = {}


def _download_gif_bytes(url: str) -> bytes:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.content


def _visual_move_line(message: str) -> str:
    match = _MOVE_MESSAGE.match(message)
    if match is None:
        return message
    return f"{match.group('pokemon')} uses {match.group('move')}!"


class BattleGifArenaView(BattleArenaView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._started = False
        self._gif_bytes: dict[str, bytes] = {}
        self._gif_filenames: dict[str, str] = {}
        self._active_sprites: dict[str, tuple[int, bool] | None] = {
            "side_a": None,
            "side_b": None,
        }
        self._caption = "Battle started."
        self._last_step: BattleStep | None = None
        self._pending_move: str | None = None

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
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)

        try:
            battle = await self.core.battle_application_service.get_battle(
                self.battle_id,
            )
            if not battle.is_ready:
                self._started = False
                for child in self.children:
                    child.disabled = False
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
            result = await self.core.battle_execution_service.run_battle(
                self.battle_id,
                initiator_display_name=self._side_a_name,
                opponent_display_name=self._side_b_name,
            )
            await self.core.battle_replay_service.replay(
                result.steps,
                self._on_step,
            )
            await self._show_final_result(result)
        except Exception:
            logger.exception("Experimental GIF battle failed")
            try:
                await interaction.followup.send(
                    "⚠️ Battle finished, but it could not be displayed correctly.",
                    ephemeral=True,
                )
            except Exception:
                logger.exception("Could not report GIF battle failure")

    async def _on_step(
        self,
        step: BattleStep,
        recent_lines: tuple[str, ...],
    ) -> None:
        self._last_step = step
        if step.step_type is BattleStepType.MOVE:
            self._pending_move = _visual_move_line(step.message)
            return

        if step.step_type is BattleStepType.DAMAGE:
            return

        if step.step_type is BattleStepType.ATTACK:
            move_line = self._pending_move
            self._pending_move = None
            damage_line = step.message
            if move_line and move_line in damage_line:
                caption = damage_line
            elif move_line:
                caption = f"{move_line}\n{damage_line}"
            else:
                caption = damage_line
            self._caption = caption
        elif step.step_type is BattleStepType.SWITCH:
            match = _SWITCH_MESSAGE.search(step.message)
            active_name = match.group("pokemon") if match else "Pokémon"
            self._caption = f"{active_name} enters the battle!"
        elif step.step_type is BattleStepType.START:
            self._caption = "Battle started."
        else:
            return

        await self._update_message(step)

    async def _update_message(self, step: BattleStep) -> None:
        await self._ensure_gifs(step)
        if self.message is None:
            return

        attachments = None
        if step.step_type in {BattleStepType.START, BattleStepType.SWITCH}:
            attachments = self._build_attachments()

        await self.message.edit(
            embed=self._build_replay_embed(step),
            view=self,
            **({"attachments": attachments} if attachments is not None else {}),
        )

    async def _ensure_gifs(self, step: BattleStep) -> None:
        for side_key, side_name, side_a in (
            ("side_a", self._side_a_name, True),
            ("side_b", self._side_b_name, False),
        ):
            sprite = self._pokeapi_for_side(side_name, step)
            if self._active_sprites[side_key] == sprite:
                continue
            url = (
                battle_initiator_sprite_url(sprite[0], shiny=sprite[1])
                if side_a
                else battle_opponent_sprite_url(sprite[0], shiny=sprite[1])
            )
            if url not in self._gif_bytes:
                try:
                    self._gif_bytes[url] = await asyncio.to_thread(
                        self._load_gif_bytes,
                        url,
                    )
                    self._gif_filenames[url] = (
                        "player.gif" if side_a else "opponent.gif"
                    )
                except Exception:
                    logger.exception("Could not load battle GIF: %s", url)
                    self._gif_bytes[url] = await asyncio.to_thread(
                        self._load_fallback_bytes,
                        sprite[0],
                        sprite[1],
                    )
                    self._gif_filenames[url] = (
                        "player.png" if side_a else "opponent.png"
                    )
            self._active_sprites[side_key] = sprite

    @staticmethod
    def _load_gif_bytes(url: str) -> bytes:
        cached = _GIF_BYTES_CACHE.get(url)
        if cached is not None:
            return cached
        data = _download_gif_bytes(url)
        _GIF_BYTES_CACHE[url] = data
        return data

    @staticmethod
    def _load_fallback_bytes(pokeapi_id: int, shiny: bool) -> bytes:
        buffer = io.BytesIO()
        BattleAssets().get_sprite(pokeapi_id, shiny=shiny).save(buffer, format="PNG")
        return buffer.getvalue()

    def _build_attachments(self) -> list[discord.File]:
        side_a_url = battle_initiator_sprite_url(
            self._active_sprites["side_a"][0],
            shiny=self._active_sprites["side_a"][1],
        )
        side_b_url = battle_opponent_sprite_url(
            self._active_sprites["side_b"][0],
            shiny=self._active_sprites["side_b"][1],
        )
        return [
            discord.File(
                io.BytesIO(self._gif_bytes[side_a_url]),
                filename=self._gif_filenames[side_a_url],
            ),
            discord.File(
                io.BytesIO(self._gif_bytes[side_b_url]),
                filename=self._gif_filenames[side_b_url],
            ),
        ]

    def _build_replay_embed(self, step: BattleStep) -> discord.Embed:
        return discord.Embed(
            title="⚔️ Battle GIF",
            description=f"{self._caption}\n\n{self._hp_lines(step)}",
            color=discord.Color.gold(),
        )

    def _hp_lines(self, step: BattleStep) -> str:
        lines = []
        for side_name in (self._side_a_name, self._side_b_name):
            state = step.state_snapshot.get(side_name, {})
            active_name = state.get("active_name", "Pokémon")
            hp = state.get("hp", [0])[0]
            hp_max = state.get("hp_max", [0])[0]
            lines.append(f"{active_name}: {hp}/{hp_max} HP")
        return "\n".join(lines)

    async def _show_final_result(self, result) -> None:
        if self.message is None:
            return
        winner = (
            self._side_a_name
            if result.winner_trainer_id == self.initiator_id
            else (
                self._side_b_name
                if result.winner_trainer_id == self.opponent_id
                else result.winner_side_name
            )
        )
        final_step = result.steps[-1] if result.steps else self._last_step
        if final_step is None:
            return
        self._caption = f"🏆 Battle Complete\n{winner} wins!"
        await self._update_message(final_step)
