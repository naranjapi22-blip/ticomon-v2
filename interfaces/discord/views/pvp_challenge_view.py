from __future__ import annotations

import asyncio
import io
import logging
import time
from dataclasses import replace

import discord

from application.pvp.models import PvpAction, PvpActionKind
from application.pvp.presentation_adapter import pvp_presentation_state
from application.pvp.snapshots import PvpBattleSnapshot
from core.pvp.session import PvpPhase
from interfaces.discord.views.creature_selection_view import CreatureSelectionView

logger = logging.getLogger(__name__)


def _safe_display_name(name: object) -> str:
    if name is None:
        return "Trainer"
    value = str(name).replace("\r", " ").replace("\n", " ").strip()
    if not value:
        return "Trainer"
    return value[:24]


class PvpChallengeView(discord.ui.View):
    def __init__(
        self, core, session, display_names: dict[int, str] | None = None
    ) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.session_id = session.id
        self.opponent_id = session.opponent_id
        self.display_names = dict(display_names or {})
        self.message: discord.Message | None = None

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
            session.phase = PvpPhase.TEAM_SELECTION
        except ValueError:
            await interaction.response.send_message(
                "This PvP challenge is no longer active.", ephemeral=True
            )
            return

        view = PvpTeamSelectionView(self.core, session, self.display_names)
        view.message = self.message
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=(
                "PvP challenge accepted. Each trainer must privately select "
                "and confirm three creatures."
            ),
            view=view,
        )
        if self.message is None:
            self.message = interaction.message
        view.message = self.message
        await interaction.followup.send(
            "Use **Select team** below to choose your three PvP creatures.",
            ephemeral=True,
        )

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button) -> None:
        await self.core.pvp_application_service.decline(self.session_id)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="PvP challenge declined.",
            view=self,
        )

    async def on_timeout(self) -> None:
        await self.core.pvp_application_service.cleanup(self.session_id)
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class PvpTeamConfirmView(discord.ui.View):
    def __init__(self, team_view: "PvpTeamSelectionView") -> None:
        super().__init__(timeout=180)
        self.team_view = team_view

    @discord.ui.button(label="Confirm team", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            ready = await self.team_view.confirm(interaction.user.id)
        except Exception as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        if not ready:
            await interaction.followup.send(
                "Your team is confirmed. Waiting for the other trainer.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            "Both teams are confirmed. Starting PvP…", ephemeral=True
        )


class PvpTeamSelectionView(discord.ui.View):
    def __init__(
        self, core, session, display_names: dict[int, str] | None = None
    ) -> None:
        super().__init__(timeout=600)
        self.core = core
        self.session_id = session.id
        self.player_ids = session.player_ids
        self.display_names = dict(display_names or {})
        self.message: discord.Message | None = None
        self.board: PvpBoardView | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.player_ids:
            await interaction.response.send_message(
                "You are not part of this PvP session.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Pick Your Team", style=discord.ButtonStyle.primary, emoji="📋"
    )
    async def select_team(self, interaction: discord.Interaction, button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            options = await self.core.pvp_application_service.get_team_selector(
                interaction.user.id
            )
        except (ValueError, TypeError, RuntimeError) as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        if len(options) < 3:
            await interaction.followup.send(
                "❌ Configure at least 3 eligible creatures in your team first.",
                ephemeral=True,
            )
            return
        selection_view = CreatureSelectionView(
            owner_id=interaction.user.id,
            required_count=3,
            options=options,
            on_selected=lambda selected: self.core.pvp_application_service.select_team(
                self.session_id, interaction.user.id, selected
            ),
            success_message=lambda team: (
                "Your selection is saved. Confirm it when ready:"
            ),
            success_view=lambda _team: PvpTeamConfirmView(self),
        )
        await interaction.followup.send(
            "Choose exactly **3** Pokémon from your collection.",
            view=selection_view,
            ephemeral=True,
        )

    async def confirm(self, trainer_id: int) -> bool:
        return await self.core.pvp_application_service.confirm_team(
            self.session_id,
            trainer_id,
            on_event=self._on_event,
            on_finished=self._on_finished,
            on_snapshot=self._on_snapshot,
        )

    async def _on_event(self, message: str) -> None:
        if self.message is None:
            return
        board = await self._get_board()
        await board.set_event(message)

    async def _on_snapshot(self, snapshot: PvpBattleSnapshot) -> None:
        if self.message is None:
            return
        board = await self._get_board()
        await board.set_snapshot(snapshot)

    async def _get_board(self) -> "PvpBoardView":
        if self.board is None:
            self.board = await PvpBoardView.from_selection(self)
        return self.board

    async def _on_finished(self, battle: object) -> None:
        if self.message is None:
            return
        board = await self._get_board()
        board.current_event = "Battle finished."
        await board.finish()

    async def on_timeout(self) -> None:
        await self.core.pvp_application_service.cleanup(self.session_id)
        for child in self.children:
            child.disabled = True


class PvpBoardView(discord.ui.View):
    def __init__(self, source: PvpTeamSelectionView) -> None:
        super().__init__(timeout=1800)
        self.core = source.core
        self.session_id = source.session_id
        self.message = source.message
        self.source = source
        self.display_names = dict(getattr(source, "display_names", {}))
        self.current_event = "Choose an action."
        self.ready: set[int] = set()
        self.snapshot: PvpBattleSnapshot | None = None
        self._snapshots: dict[int, PvpBattleSnapshot] = {}
        self._pending_edit: tuple[str, tuple] | None = None
        self._edit_task: asyncio.Task | None = None
        self._last_edit_at = 0.0
        self._last_render: tuple[str, tuple] | None = None
        self._edit_interval = 0.5
        self._visual_version = 0
        self._last_visual_version = -1
        self._last_visual_bytes: bytes | None = None
        self._terminal = False

    @classmethod
    async def from_selection(cls, source: PvpTeamSelectionView) -> "PvpBoardView":
        board = cls(source)
        if source.message is not None:
            await board._edit_message()
        return board

    def render(self) -> str:
        try:
            session = self.core.pvp_application_service.registry.get(self.session_id)
        except ValueError:
            return "PvP session finished."
        ready = ", ".join(f"<@{player_id}>" for player_id in self.ready) or "none"
        active_lines = self._render_players(session)
        turn = self.snapshot.turn if self.snapshot is not None else session.turn_number
        result = (
            f"⚔️ PvP — Turn {turn}\n"
            f"<@{session.initiator_id}> vs <@{session.opponent_id}>\n\n"
            + "\n".join(active_lines)
            + "\n\n"
            f"{self.current_event}"
        )
        if getattr(self.core, "battle_presentation_renderer", None) is None:
            result += f"\nReady: {ready}"
        return result

    def _render_players(self, session) -> list[str]:
        if self.snapshot is None:
            lines = []
            for player_id in session.player_ids:
                team = session.selected_creatures.get(player_id, ())
                if team:
                    lines.append(
                        f"<@{player_id}>: {team[0].species.name} — 100% HP — "
                        f"{len(team)} remaining"
                    )
                else:
                    lines.append(f"<@{player_id}>: team pending")
            return lines

        snapshot = self._display_snapshot()
        player = snapshot.player_active
        opponent = snapshot.opponent_active
        return [
            self._format_snapshot_player(
                snapshot.player_id,
                player,
                snapshot.player_remaining,
            ),
            self._format_snapshot_player(
                snapshot.opponent_id,
                opponent,
                snapshot.opponent_remaining,
            ),
        ]

    def _display_snapshot(self) -> PvpBattleSnapshot:
        assert self.snapshot is not None
        session = self.core.pvp_application_service.registry.get(self.session_id)
        canonical = self._snapshots.get(session.initiator_id, self.snapshot)
        if canonical.player_id == session.opponent_id:
            canonical = replace(
                canonical,
                player_id=session.initiator_id,
                opponent_id=session.opponent_id,
                player_active=canonical.opponent_active,
                opponent_active=canonical.player_active,
                player_remaining=canonical.opponent_remaining,
                opponent_remaining=canonical.player_remaining,
                force_switch_player=canonical.force_switch_opponent,
                force_switch_opponent=canonical.force_switch_player,
            )
        opponent = self._snapshots.get(session.opponent_id)
        if opponent is None:
            return canonical
        return replace(
            canonical,
            force_switch_opponent=opponent.force_switch_player,
            finished=canonical.finished or opponent.finished,
            winner_id=canonical.winner_id or opponent.winner_id,
            tie=canonical.tie and opponent.tie,
        )

    @staticmethod
    def _format_snapshot_player(player_id, pokemon, remaining: int) -> str:
        if pokemon is None:
            return f"<@{player_id}>: waiting for Pokémon — {remaining} remaining"
            return f"<@{player_id}>: waiting for Pokémon — {remaining} remaining"
        hp = f"{pokemon.hp_fraction:.0%} HP"
        status = f" · {pokemon.status}" if pokemon.status else ""
        return (
            f"<@{player_id}>: {pokemon.species_name} — {hp}{status} — "
            f"{remaining} remaining"
        )

    async def set_event(self, message: str) -> None:
        self.current_event = message
        self.ready.clear()
        await self._edit_message()

    async def set_snapshot(self, snapshot: PvpBattleSnapshot) -> None:
        self._snapshots[snapshot.player_id] = snapshot
        self.snapshot = snapshot
        self._visual_version += 1
        await self._edit_message()

    async def finish(self, snapshot: PvpBattleSnapshot | None = None) -> None:
        if snapshot is not None:
            self._snapshots[snapshot.player_id] = snapshot
            self.snapshot = snapshot
        self._terminal = True
        self._visual_version += 1
        await self._edit_message(force=True)
        if self._edit_task is not None:
            await self._edit_task

    async def _edit_message(self, *, force: bool = False) -> None:
        if self.message is None:
            return
        state = (self.render(), self._component_signature())
        if not force and (state == self._last_render or state == self._pending_edit):
            return
        self._pending_edit = state
        if self._edit_task is None or self._edit_task.done():
            self._edit_task = asyncio.create_task(self._flush_edits())

    def _component_signature(self) -> tuple:
        return tuple(
            (
                getattr(child, "custom_id", None),
                getattr(child, "label", None),
                getattr(child, "disabled", None),
            )
            for child in self.children
        )

    async def _flush_edits(self) -> None:
        while self._pending_edit is not None and self.message is not None:
            wait = self._edit_interval - (time.monotonic() - self._last_edit_at)
            if wait > 0:
                await asyncio.sleep(wait)
            state = self._pending_edit
            self._pending_edit = None
            if state == self._last_render:
                continue
            content, _ = state
            visual_state = self._visual_state()
            visual_bytes = self._last_visual_bytes
            renderer = getattr(self.core, "battle_presentation_renderer", None)
            visual_version = self._visual_version
            image_updated = False
            if renderer is not None and visual_state is not None:
                try:
                    if visual_version != self._last_visual_version:
                        visual_bytes = await asyncio.to_thread(
                            renderer.render_to_bytes, visual_state
                        )
                        if (
                            visual_version != self._visual_version
                            and not self._terminal
                        ):
                            await self._edit_message()
                            continue
                        self._last_visual_bytes = visual_bytes
                        self._last_visual_version = visual_version
                        image_updated = True
                except Exception:
                    logger.exception(
                        "PvP presentation render failed session_id=%s",
                        self.session_id,
                    )
                    visual_bytes = self._last_visual_bytes
            try:
                edit_kwargs: dict[str, object] = {
                    "content": content,
                    "view": None if self._terminal else self,
                }
                if visual_bytes is not None:
                    edit_kwargs["embed"] = self._build_embed(visual_state)
                if image_updated and visual_bytes is not None:
                    edit_kwargs["attachments"] = [
                        discord.File(
                            io.BytesIO(visual_bytes), filename="pvp-battle.gif"
                        )
                    ]
                await self.message.edit(**edit_kwargs)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                self._pending_edit = None
                try:
                    await self.core.pvp_application_service.cleanup(self.session_id)
                except Exception:
                    logger.exception(
                        "PvP board cleanup failed session_id=%s", self.session_id
                    )
                return
            self._last_render = state
            self._last_edit_at = time.monotonic()

    def _visual_state(self):
        if self.snapshot is None:
            return None
        try:
            session = self.core.pvp_application_service.registry.get(self.session_id)
        except ValueError:
            return None
        snapshot = self._display_snapshot()
        state = pvp_presentation_state(
            snapshot,
            player_name=self._visible_name(session.initiator_id),
            opponent_name=self._visible_name(session.opponent_id),
            last_event=self.current_event,
        )
        if self._terminal and not state.terminal:
            return replace(state, terminal=True)
        return state

    def _visible_name(self, player_id: int) -> str:
        return _safe_display_name(self.display_names.get(player_id))

    def _build_embed(self, visual_state) -> discord.Embed:
        if visual_state is not None and visual_state.terminal:
            if visual_state.draw:
                description = "The battle ended in a draw."
            else:
                winner = visual_state.winner_id
                description = (
                    f"{self._visible_name(winner)} wins the battle!"
                    if winner
                    else "The battle ended."
                )
            title = "🏆 PvP Battle Complete"
        else:
            description = self.current_event
            title = "⚔️ PvP Battle"
        embed = discord.Embed(title=title, description=description)
        embed.set_image(url="attachment://pvp-battle.gif")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            session = self.core.pvp_application_service.registry.get(self.session_id)
        except ValueError:
            await interaction.response.send_message(
                "This PvP session is no longer active.", ephemeral=True
            )
            return False
        if interaction.user.id not in session.player_ids:
            await interaction.response.send_message(
                "You are not part of this PvP session.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Choose action", style=discord.ButtonStyle.primary)
    async def choose_action(self, interaction: discord.Interaction, button) -> None:
        try:
            actions = self.core.pvp_application_service.legal_actions_for(
                self.session_id, interaction.user.id
            )
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            "Choose a legal action:",
            view=PvpActionView(self, actions),
            ephemeral=True,
        )

    @discord.ui.button(label="Forfeit", style=discord.ButtonStyle.danger)
    async def forfeit(self, interaction: discord.Interaction, button) -> None:
        await self.core.pvp_application_service.forfeit(
            self.session_id, interaction.user.id
        )
        await interaction.response.edit_message(
            content="You forfeited the PvP battle.", view=None
        )

    async def on_timeout(self) -> None:
        if self._edit_task is not None and not self._edit_task.done():
            self._edit_task.cancel()
        await self.core.pvp_application_service.cleanup(self.session_id)


class PvpActionView(discord.ui.View):
    def __init__(self, board: PvpBoardView, actions) -> None:
        super().__init__(timeout=30)
        self.board = board
        self.actions = {action.identifier: action for action in actions.all_actions}
        for action in self.actions.values():
            button = discord.ui.Button(
                label=action.label[:80],
                style=(
                    discord.ButtonStyle.secondary
                    if action.kind is PvpActionKind.SWITCH
                    else discord.ButtonStyle.primary
                ),
                custom_id=f"pvp-action:{board.session_id}:{action.identifier}",
            )
            button.callback = self._callback(action)
            self.add_item(button)

    def _callback(self, action: PvpAction):
        async def callback(interaction: discord.Interaction) -> None:
            try:
                accepted = await self.board.core.pvp_application_service.submit_action(
                    self.board.session_id,
                    interaction.user.id,
                    action,
                )
            except ValueError as error:
                await interaction.response.send_message(str(error), ephemeral=True)
                return
            if not accepted:
                await interaction.response.send_message(
                    "That action window has already been resolved.", ephemeral=True
                )
                return
            self.board.ready.add(interaction.user.id)
            await interaction.response.edit_message(
                content="Action selected.", view=None
            )
            if self.board.message is not None:
                await self.board._edit_message()

        return callback
