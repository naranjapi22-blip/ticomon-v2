from __future__ import annotations

import logging

import discord

from application.creature.creature_loadout_service import CreatureLoadout

logger = logging.getLogger(__name__)

PAGE_SIZE = 23  # Leave room for an empty slot and a selected off-page move.
EMPTY_MOVE = "__empty__"


def _validate_select_values(select: discord.ui.Select) -> None:
    if not 1 <= len(select.options) <= 25:
        raise ValueError("Move editor generated too many Discord select options.")
    if select.placeholder is not None and not 1 <= len(select.placeholder) <= 150:
        raise ValueError("Move editor generated an invalid Discord placeholder.")
    if not 1 <= len(select.custom_id) <= 100:
        raise ValueError("Move editor generated an invalid Discord custom ID.")
    default_count = 0
    for option in select.options:
        if not isinstance(option.label, str) or not 1 <= len(option.label) <= 100:
            raise ValueError("Move editor generated an invalid Discord option label.")
        if not isinstance(option.value, str) or not 1 <= len(option.value) <= 100:
            raise ValueError("Move editor generated an invalid Discord select value.")
        if option.description is not None and not 1 <= len(option.description) <= 100:
            raise ValueError(
                "Move editor generated an invalid Discord option description."
            )
        default_count += option.default
    if default_count != 1:
        raise ValueError("Move editor must have exactly one default option per select.")


def _loadout_context(loadout: CreatureLoadout, owner_id: int) -> dict[str, object]:
    creature = loadout.creature
    species = creature.species
    return {
        "creature_id": getattr(creature, "id", None),
        "species_id": getattr(species, "id", None),
        "collection_number": getattr(creature, "collection_number", None),
        "owner_id": owner_id,
        "legal_move_count": len(loadout.legal_moves),
    }


async def _send_ephemeral_once(interaction, content: str) -> None:
    response = interaction.response
    is_done = getattr(response, "is_done", False)
    if callable(is_done):
        is_done = is_done()
    if is_done:
        followup = getattr(interaction, "followup", None)
        send = getattr(followup, "send", None)
        if send is not None:
            await send(content, ephemeral=True)
        return
    await response.send_message(content, ephemeral=True)


def _value(value) -> str:
    return str(value) if value is not None else "—"


def render_loadout(loadout: CreatureLoadout) -> str:
    creature = loadout.creature
    ability = loadout.ability.display_name if loadout.ability else creature.ability_id
    ability_effect = (
        getattr(loadout.ability, "effect", None) if loadout.ability else None
    ) or "Effect unavailable."
    lines = [
        f"**#{creature.collection_number} {creature.species.name}**",
        f"Species: {creature.species.name}",
        f"Ability: {ability or '—'}",
        f"Effect: {ability_effect}",
        "",
    ]
    if not loadout.moves:
        lines.append("No moves equipped.")
    for index, move in enumerate(loadout.moves, 1):
        lines.append(
            f"{index}. **{move.display_name}** — {move.move_type.title()} · "
            f"{move.category} · Power {_value(move.base_power)} · "
            f"Accuracy {_value(move.accuracy)} · PP {move.pp}"
        )
    return "\n".join(lines)


class MoveLoadoutView(discord.ui.View):
    def __init__(self, service, loadout: CreatureLoadout, *, owner_id: int) -> None:
        super().__init__(timeout=180)
        self.service = service
        self.loadout = loadout
        self.owner_id = owner_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the owner can edit these moves.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Change Moves", style=discord.ButtonStyle.primary)
    async def change_moves(self, interaction, button) -> None:
        try:
            editor = MoveEditorView(self.service, self.loadout, self.owner_id)
            editor.message = self.message or interaction.message
            await interaction.response.edit_message(
                content=render_loadout(self.loadout) + "\n\nSelect 1 to 4 moves.",
                view=editor,
            )
        except Exception:
            logger.exception(
                "move editor failed to open context=%s",
                _loadout_context(self.loadout, self.owner_id),
            )
            await _send_ephemeral_once(
                interaction,
                "I could not open the moves editor. Please try again later.",
            )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class MoveSlotSelect(discord.ui.Select):
    def __init__(self, editor, slot_index: int, options, *, placeholder: str) -> None:
        self.editor = editor
        self.slot_index = slot_index
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"move-slot-{slot_index + 1}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.editor._handle_move_selection(interaction, self.slot_index, self)


class MoveEditorView(discord.ui.View):
    def __init__(self, service, loadout: CreatureLoadout, owner_id: int) -> None:
        super().__init__(timeout=180)
        self.service = service
        self.loadout = loadout
        self.owner_id = owner_id
        self.message = None
        self.legal_moves = list(loadout.legal_moves)
        self.selected = list(loadout.creature.moves[:4])
        self.selected.extend([""] * (4 - len(self.selected)))
        self.page = 0
        self._refresh_selects()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the owner can edit these moves.", ephemeral=True
            )
            return False
        return True

    def _refresh_selects(self) -> None:
        for child in list(self.children):
            if isinstance(child, MoveSlotSelect):
                self.remove_item(child)
        start = self.page * PAGE_SIZE
        page_moves = list(self.legal_moves[start : start + PAGE_SIZE])
        move_by_id = {move.id: move for move in self.legal_moves}
        for slot_index in range(4):
            selected_value = self.selected[slot_index]
            if selected_value not in move_by_id:
                selected_value = ""
                self.selected[slot_index] = selected_value
            visible_moves = list(page_moves)
            if selected_value and selected_value not in {
                move.id for move in visible_moves
            }:
                visible_moves.insert(0, move_by_id[selected_value])
            options = [
                discord.SelectOption(
                    label="Empty slot",
                    value=EMPTY_MOVE,
                    default=not selected_value,
                )
            ]
            options.extend(
                discord.SelectOption(
                    label=move.display_name[:100],
                    value=move.id,
                    default=move.id == selected_value,
                )
                for move in visible_moves
            )
            placeholder = (
                move_by_id[selected_value].display_name
                if selected_value
                else f"Move slot {slot_index + 1}"
            )
            select = MoveSlotSelect(self, slot_index, options, placeholder=placeholder)
            _validate_select_values(select)
            self.add_item(select)
        self._validate_component_rows()

    def _validate_component_rows(self) -> None:
        components = self.to_components()
        if len(components) > 5:
            raise ValueError("Move editor generated more than five component rows.")

    async def _handle_move_selection(self, interaction, slot_index, select) -> None:
        value = select.values[0]
        if value == EMPTY_MOVE:
            value = ""
        other_values = self.selected[:slot_index] + self.selected[slot_index + 1 :]
        if value and value in other_values:
            await interaction.response.send_message(
                "A creature cannot equip duplicate moves.", ephemeral=True
            )
            return
        self.selected[slot_index] = value
        self._refresh_selects()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, row=4)
    async def previous(self, interaction, button) -> None:
        self.page = max(0, self.page - 1)
        self._refresh_selects()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, row=4)
    async def next(self, interaction, button) -> None:
        self.page = min(max(0, (len(self.legal_moves) - 1) // PAGE_SIZE), self.page + 1)
        self._refresh_selects()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Save Moves", style=discord.ButtonStyle.success, row=4)
    async def save(self, interaction, button) -> None:
        try:
            loadout = await self.service.update_moves(
                self.owner_id,
                self.loadout.creature.collection_number,
                tuple(item for item in self.selected if item),
            )
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=render_loadout(loadout), view=self
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=4)
    async def cancel(self, interaction, button) -> None:
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=render_loadout(self.loadout) + "\n\nNo changes saved.", view=self
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
