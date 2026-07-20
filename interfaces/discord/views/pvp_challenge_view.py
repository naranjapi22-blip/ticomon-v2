from __future__ import annotations

import asyncio
from dataclasses import replace

import discord

from application.pvp.models import PvpAction, PvpActionKind
from application.pvp.snapshots import PvpBattleSnapshot
from core.pvp.session import PvpPhase


class PvpChallengeView(discord.ui.View):
    def __init__(self, core, session) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.session_id = session.id
        self.opponent_id = session.opponent_id
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

        view = PvpTeamSelectionView(self.core, session)
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


class PvpTeamModal(discord.ui.Modal, title="Select PvP team"):
    collection_numbers = discord.ui.TextInput(
        label="Collection numbers",
        placeholder="Example: 12, 18, 27",
        min_length=1,
        max_length=40,
    )

    def __init__(self, view: "PvpTeamSelectionView") -> None:
        super().__init__()
        self.team_view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            numbers = tuple(
                int(value.strip())
                for value in str(self.collection_numbers.value).split(",")
                if value.strip()
            )
            team = await self.team_view.core.pvp_application_service.select_team(
                self.team_view.session_id,
                interaction.user.id,
                numbers,
            )
        except (ValueError, TypeError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        summary = "\n".join(
            f"#{creature.collection_number} {creature.species.name} — "
            f"{creature.ability_id} — {', '.join(creature.moves)}"
            for creature in team
        )
        await interaction.response.send_message(
            f"Your selection is saved. Confirm it when ready:\n{summary}",
            view=PvpTeamConfirmView(self.team_view),
            ephemeral=True,
        )


class PvpTeamConfirmView(discord.ui.View):
    def __init__(self, team_view: "PvpTeamSelectionView") -> None:
        super().__init__(timeout=180)
        self.team_view = team_view

    @discord.ui.button(label="Confirm team", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button) -> None:
        try:
            ready = await self.team_view.confirm(interaction.user.id)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        if not ready:
            await interaction.response.send_message(
                "Your team is confirmed. Waiting for the other trainer.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "Both teams are confirmed. Starting PvP…", ephemeral=True
        )


class PvpTeamSelectionView(discord.ui.View):
    def __init__(self, core, session) -> None:
        super().__init__(timeout=600)
        self.core = core
        self.session_id = session.id
        self.player_ids = session.player_ids
        self.message: discord.Message | None = None
        self.board: PvpBoardView | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.player_ids:
            await interaction.response.send_message(
                "You are not part of this PvP session.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Select team", style=discord.ButtonStyle.primary)
    async def select_team(self, interaction: discord.Interaction, button) -> None:
        await interaction.response.send_modal(PvpTeamModal(self))

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
        try:
            await self.message.edit(content="PvP finished.", view=None)
        except discord.HTTPException:
            pass

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
        self.current_event = "Choose an action."
        self.ready: set[int] = set()
        self.snapshot: PvpBattleSnapshot | None = None
        self._snapshots: dict[int, PvpBattleSnapshot] = {}

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
        return (
            f"⚔️ PvP — Turn {turn}\n"
            f"<@{session.initiator_id}> vs <@{session.opponent_id}>\n\n"
            + "\n".join(active_lines)
            + "\n\n"
            f"{self.current_event}\n"
            f"Ready: {ready}"
        )

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
        await self._edit_message()

    async def _edit_message(self) -> None:
        if self.message is None:
            return
        try:
            await self.message.edit(content=self.render(), view=self)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            asyncio.create_task(
                self.core.pvp_application_service.cleanup(self.session_id)
            )

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
                await self.board.core.pvp_application_service.submit_action(
                    self.board.session_id,
                    interaction.user.id,
                    action,
                )
            except ValueError as error:
                await interaction.response.send_message(str(error), ephemeral=True)
                return
            self.board.ready.add(interaction.user.id)
            await interaction.response.edit_message(
                content="Action selected.", view=None
            )
            if self.board.message is not None:
                await self.board.message.edit(
                    content=self.board.render(), view=self.board
                )

        return callback
