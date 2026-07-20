from __future__ import annotations

import discord

from application.creature.creature_loadout_service import CreatureLoadout

PAGE_SIZE = 24  # Keep one option available for the empty slot.


def _value(value) -> str:
    return str(value) if value is not None else "—"


def render_loadout(loadout: CreatureLoadout) -> str:
    creature = loadout.creature
    ability = loadout.ability.display_name if loadout.ability else creature.ability_id
    lines = [
        f"**#{creature.collection_number} {creature.species.name}**",
        f"Species: {creature.species.name}",
        f"Ability: {ability or '—'}",
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
        editor = MoveEditorView(self.service, self.loadout, self.owner_id)
        editor.message = self.message or interaction.message
        await interaction.response.edit_message(
            content=render_loadout(self.loadout) + "\n\nSelect 1 to 4 moves.",
            view=editor,
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class MoveEditorView(discord.ui.View):
    def __init__(self, service, loadout: CreatureLoadout, owner_id: int) -> None:
        super().__init__(timeout=180)
        self.service = service
        self.loadout = loadout
        self.owner_id = owner_id
        self.message = None
        self.legal_moves = list(loadout.legal_moves)
        self.selected = list(loadout.creature.moves)
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
            if isinstance(child, discord.ui.Select):
                self.remove_item(child)
        start = self.page * PAGE_SIZE
        options = [
            discord.SelectOption(label=move.display_name[:100], value=move.id)
            for move in self.legal_moves[start : start + PAGE_SIZE]
        ]
        for slot in range(4):
            select = discord.ui.Select(
                placeholder=f"Move slot {slot + 1}",
                options=[discord.SelectOption(label="None", value="")] + options,
                min_values=1,
                max_values=1,
                custom_id=f"move-slot-{slot + 1}",
            )
            if slot < len(self.selected):
                for option in select.options:
                    option.default = option.value == self.selected[slot]
            select.callback = self._select_callback(slot, select)
            self.add_item(select)

    def _select_callback(self, slot, select):
        async def callback(interaction):
            value = select.values[0]
            if value and value in self.selected[:slot] + self.selected[slot + 1 :]:
                await interaction.response.send_message(
                    "A creature cannot equip duplicate moves.", ephemeral=True
                )
                return
            while len(self.selected) <= slot:
                self.selected.append("")
            self.selected[slot] = value
            self.selected = [item for item in self.selected if item]
            await interaction.response.edit_message(view=self)

        return callback

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
