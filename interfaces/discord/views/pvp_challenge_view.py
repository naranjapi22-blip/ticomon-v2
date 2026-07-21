from __future__ import annotations

import asyncio
import io
import logging
import time
from dataclasses import replace

import discord

from application.pvp.events import display_species_name
from application.pvp.models import PvpAction, PvpActionKind, PvpPresentationStep
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
            if session.phase is not PvpPhase.CHALLENGE:
                raise ValueError("This PvP challenge is no longer pending.")
            session.phase = PvpPhase.TEAM_SELECTION
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
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
        try:
            session = self.core.pvp_application_service.registry.get(self.session_id)
            if session.phase is not PvpPhase.CHALLENGE:
                await interaction.response.send_message(
                    "This PvP challenge is no longer pending.", ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "This PvP challenge is no longer active.", ephemeral=True
            )
            return
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
                await self.message.edit(view=None)
            except discord.HTTPException:
                logger.debug(
                    "Unable to remove expired PvP challenge controls session_id=%s",
                    self.session_id,
                    exc_info=True,
                )
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
        get_board = getattr(self.team_view, "_get_board", None)
        if get_board is not None:
            await get_board()
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

    async def _on_event(self, step: PvpPresentationStep | str) -> None:
        if self.message is None:
            return
        board = await self._get_board()
        await board.set_event(step)

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
        await board.finish()

    async def on_timeout(self) -> None:
        await self.core.pvp_application_service.cleanup(self.session_id)
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                logger.debug(
                    "Unable to remove expired PvP team controls session_id=%s",
                    self.session_id,
                    exc_info=True,
                )


class PvpBoardView(discord.ui.View):
    def __init__(self, source: PvpTeamSelectionView) -> None:
        super().__init__(timeout=1800)
        self.core = source.core
        self.session_id = source.session_id
        self.message = source.message
        self.source = source
        self.display_names = dict(getattr(source, "display_names", {}))
        self.current_event = ""
        self.recent_events: list[str] = []
        self.ready: set[int] = set()
        self.snapshot: PvpBattleSnapshot | None = None
        self._snapshots: dict[int, PvpBattleSnapshot] = {}
        self._snapshot_turns: dict[int, int] = {}
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
        active_lines = self._render_players(session)
        turn = self.snapshot.turn if self.snapshot is not None else session.turn_number
        initiator_name = self._visible_name(session.initiator_id)
        opponent_name = self._visible_name(session.opponent_id)
        waiting = self._waiting_status(session)
        lines = [
            f"{initiator_name} vs {opponent_name}",
            f"Turn {turn} · {waiting}",
            "",
            *active_lines,
        ]
        if self.current_event:
            lines.extend(("", self.current_event))
        return "\n".join(lines)

    def _render_players(self, session) -> list[str]:
        if self.snapshot is None:
            lines = []
            for player_id in (session.initiator_id, session.opponent_id):
                team = session.selected_creatures.get(player_id, ())
                if team:
                    lines.append(f"{self._visible_name(player_id)}:")
                    lines.extend(f"  {creature.species.name}" for creature in team[:3])
                else:
                    lines.append(f"{self._visible_name(player_id)}: team pending")
            return lines

        snapshot = self._display_snapshot()
        player = snapshot.player_active
        opponent = snapshot.opponent_active
        return [
            self._format_snapshot_player(player, snapshot.player_remaining),
            self._format_snapshot_player(opponent, snapshot.opponent_remaining),
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
                player_team=canonical.opponent_team,
                opponent_team=canonical.player_team,
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
    def _format_snapshot_player(pokemon, remaining: int) -> str:
        if pokemon is None:
            return f"Waiting for Pokémon · {remaining} remaining"
        current_hp = (
            pokemon.current_hp
            if pokemon.current_hp is not None
            else round(pokemon.hp_fraction * 100)
        )
        max_hp = pokemon.max_hp or 100
        hp = f"{current_hp}/{max_hp} HP"
        status = f" · {pokemon.status}" if pokemon.status else ""
        return (
            f"{display_species_name(pokemon.species_name)} · {hp}{status} · "
            f"{remaining} remaining"
        )

    def _waiting_status(self, session) -> str:
        if self._terminal or session.phase is PvpPhase.FINISHED:
            return "Battle finished"
        if session.phase is PvpPhase.STARTING:
            return "Starting"
        if session.phase is PvpPhase.FORCED_SWITCH:
            if self.snapshot is not None and (
                self.snapshot.force_switch_player
                and self.snapshot.player_remaining <= 0
                or self.snapshot.force_switch_opponent
                and self.snapshot.opponent_remaining <= 0
            ):
                return "Battle finished"
            waiting = tuple(
                player_id
                for player_id in (session.initiator_id, session.opponent_id)
                if player_id in session.active_action_requests
            )
            if waiting:
                return f"Choose a replacement ({self._visible_name(waiting[0])})"
            return "Choose a replacement"
        if session.phase is PvpPhase.RESOLVING:
            return "Resolving turn"
        waiting = tuple(
            player_id
            for player_id in (session.initiator_id, session.opponent_id)
            if player_id in session.active_action_requests
        )
        if waiting:
            names = " and ".join(self._visible_name(player_id) for player_id in waiting)
            return f"Waiting for {names}"
        if self.snapshot is not None:
            if self.snapshot.force_switch_player:
                return (
                    f"Waiting for {self._visible_name(session.initiator_id)} to switch"
                )
            if self.snapshot.force_switch_opponent:
                return (
                    f"Waiting for {self._visible_name(session.opponent_id)} to switch"
                )
        return "Waiting for both players"

    async def set_event(self, step: PvpPresentationStep | str) -> None:
        if self._terminal:
            return
        message = step.message if isinstance(step, PvpPresentationStep) else str(step)
        if (
            message.endswith(" won the battle.")
            or message == "The battle ended in a tie."
        ):
            return
        self.current_event = message
        turn = self.snapshot.turn if self.snapshot is not None else 0
        self.recent_events.append(f"Turn {turn} · {message}"[:240])
        self.recent_events = self.recent_events[-3:]
        self.ready.clear()
        await self._edit_message()

    async def set_snapshot(self, snapshot: PvpBattleSnapshot) -> None:
        if self._terminal:
            logger.info(
                "Ignoring stale PvP snapshot session_id=%s current_phase=finished "
                "incoming_turn=%s source_player=%s reason=stale_delivery_ignored",
                self.session_id,
                snapshot.turn,
                snapshot.player_id,
            )
            return
        previous_turn = self._snapshot_turns.get(snapshot.player_id)
        if previous_turn is not None and snapshot.turn < previous_turn:
            logger.info(
                "Ignoring stale PvP snapshot session_id=%s current_phase=active "
                "current_turn=%s incoming_turn=%s source_player=%s "
                "reason=stale_delivery_ignored",
                self.session_id,
                previous_turn,
                snapshot.turn,
                snapshot.player_id,
            )
            return
        self._snapshot_turns[snapshot.player_id] = snapshot.turn
        self._snapshots[snapshot.player_id] = snapshot
        self.snapshot = snapshot
        self._visual_version += 1
        await self._edit_message()

    async def finish(self, snapshot: PvpBattleSnapshot | None = None) -> None:
        if snapshot is not None:
            self._snapshots[snapshot.player_id] = snapshot
            self.snapshot = snapshot
        self._terminal = True
        self.current_event = self._result_text()
        self._visual_version += 1
        await self._edit_message(force=True)
        if self._edit_task is not None:
            await self._edit_task

    def _result_text(self) -> str:
        snapshot = self._display_snapshot()
        if snapshot.tie:
            return "The battle ended in a draw."
        if snapshot.winner_id is not None:
            return f"{self._visible_name(snapshot.winner_id)} won the battle."
        return "The battle ended."

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
            if self._terminal and content != self.render():
                content = self.render()
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
            waiting_text=self._waiting_status(session),
        )
        if self._terminal and not state.terminal:
            return replace(state, terminal=True)
        return state

    def _visible_name(self, player_id: int) -> str:
        return _safe_display_name(self.display_names.get(player_id))

    def _build_embed(self, visual_state) -> discord.Embed:
        embed = discord.Embed()
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
            embed=self._build_action_embed(interaction.user.id, actions),
            view=PvpActionView(self, interaction.user.id, actions),
            ephemeral=True,
        )

    def _build_action_embed(self, trainer_id: int, actions) -> discord.Embed:
        title = "Choose an action"
        description = "Actions are private and must be selected for the current turn."
        try:
            session = self.core.pvp_application_service.registry.get(self.session_id)
            turn = (
                self.snapshot.turn if self.snapshot is not None else session.turn_number
            )
            title = f"Turn {turn} · Choose an action"
            snapshot = self._display_snapshot() if self.snapshot is not None else None
            own = None
            if snapshot is not None:
                if trainer_id == snapshot.player_id:
                    own = snapshot.player_active
                else:
                    own = snapshot.opponent_active
            if own is not None:
                status = f" · {own.status}" if own.status else ""
                description = (
                    f"{display_species_name(own.species_name)} · "
                    f"{own.current_hp}/{own.max_hp} HP{status}"
                )
                creature = next(
                    (
                        item
                        for item in session.selected_creatures.get(trainer_id, ())
                        if item.species.name.lower() == own.species_name.lower()
                    ),
                    None,
                )
                if creature is not None and getattr(creature, "ability_id", None):
                    description += (
                        f"\nAbility: {_display_ability_name(creature.ability_id)}"
                    )
        except ValueError:
            pass

        embed = discord.Embed(title=title, description=description)
        return embed

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
        if self.message is not None:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                logger.debug(
                    "Unable to remove expired PvP board controls session_id=%s",
                    self.session_id,
                    exc_info=True,
                )
        await self.core.pvp_application_service.cleanup(self.session_id)


class PvpActionView(discord.ui.View):
    def __init__(self, board: PvpBoardView, trainer_id: int, actions) -> None:
        super().__init__(timeout=30)
        self.board = board
        self.trainer_id = trainer_id
        self.actions = {action.identifier: action for action in actions.all_actions}
        self.select = discord.ui.Select(
            placeholder=(
                "Choose a replacement"
                if actions.forced_switch
                else "Choose a move or switch"
            ),
            options=[
                discord.SelectOption(
                    label=_display_action_name(action)[:100],
                    value=action.identifier,
                    description=_action_description(action),
                )
                for action in self.actions.values()
            ][:25],
        )
        self.select.callback = self._select_callback
        self.add_item(self.select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This private action panel belongs to another trainer.",
                ephemeral=True,
            )
            return False
        return True

    async def _select_callback(self, interaction: discord.Interaction) -> None:
        identifier = self.select.values[0]
        action = self.actions[identifier]
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
        self.select.disabled = True
        self.board.ready.add(interaction.user.id)
        await interaction.response.edit_message(
            content="Action selected. Waiting for the other player.",
            embed=None,
            view=None,
        )
        if self.board.message is not None:
            await self.board._edit_message()


def _action_detail(action: PvpAction) -> str:
    move_type = action.move_type or "—"
    category = action.category or "—"
    power = f"{action.power} BP" if action.power is not None else "—"
    accuracy = f"{action.accuracy}% Acc" if action.accuracy is not None else "—"
    detail = action.detail or "PP —"
    return f"{move_type} · {category} · {power} · {detail} · {accuracy}"


def _action_description(action: PvpAction) -> str:
    if action.kind is PvpActionKind.MOVE:
        return _action_detail(action)[:100]
    hp = (
        f"{action.hp_current}/{action.hp_max} HP"
        if action.hp_current is not None and action.hp_max is not None
        else "HP unavailable"
    )
    return f"{hp} · {'Fainted' if action.fainted else 'Healthy'}"[:100]


_DISPLAY_NAME_OVERRIDES = {
    "dazzlinggleam": "Dazzling Gleam",
    "hyperbeam": "Hyper Beam",
    "intrepidsword": "Intrepid Sword",
    "kommoo": "Kommo-o",
    "moonblast": "Moonblast",
    "playrough": "Play Rough",
    "walkingwake": "Walking Wake",
    "ironthorns": "Iron Thorns",
    "zacian": "Zacian",
}


def _display_ability_name(value: object) -> str:
    return _display_name(value)


def _display_action_name(action: PvpAction) -> str:
    if action.kind is PvpActionKind.MOVE:
        return _display_name(action.label)
    return f"Switch to {_display_name(action.label)}"


def _display_name(value: object) -> str:
    text = str(value).replace("_", "-").strip()
    key = "".join(character for character in text.casefold() if character.isalnum())
    if key in _DISPLAY_NAME_OVERRIDES:
        return _DISPLAY_NAME_OVERRIDES[key]
    return text.replace("-", " ").title()
