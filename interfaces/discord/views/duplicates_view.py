from __future__ import annotations

from collections.abc import Mapping

import discord

from interfaces.discord.application_emojis import species_emoji_prefix
from interfaces.discord.views.creature_list_view import CreatureListView

DUPLICATES_DESCRIPTION_LIMIT = 3800
DUPLICATES_LINE_LIMIT = 500


def _creature_entry(creature) -> str:
    return f"#{creature.collection_number} {creature.iv_percentage:.2f}%"


def format_duplicate_species_blocks(
    species,
    creatures: list,
    emoji_index: Mapping[str, object],
) -> list[str]:
    ordered = sorted(
        creatures,
        key=lambda creature: (
            -creature.iv_percentage,
            (
                creature.collection_number
                if creature.collection_number is not None
                else float("inf")
            ),
        ),
    )
    prefix = (
        f"{species_emoji_prefix(emoji_index, species.pokeapi_id)}"
        f"{species.name.title()} ×{len(ordered)}"
    )
    lines = []
    current = prefix

    for creature in ordered:
        entry = _creature_entry(creature)
        candidate = f"{current} • {entry}"
        if len(candidate) <= DUPLICATES_LINE_LIMIT:
            current = candidate
        else:
            lines.append(current)
            current = f"↳ • {entry}"

    lines.append(current)

    blocks = []
    current_block = []
    current_length = 0
    for line in lines:
        if (
            current_block
            and current_length + len(line) + 1 > DUPLICATES_DESCRIPTION_LIMIT
        ):
            blocks.append("\n".join(current_block))
            current_block = []
            current_length = 0
        current_block.append(line)
        current_length += len(line) + 1

    if current_block:
        blocks.append("\n".join(current_block))
    return blocks


def build_duplicate_pages(blocks: list[str]) -> list[str]:
    pages = []
    current = []
    current_length = 0
    for block in blocks:
        separator_length = 2 if current else 0
        if (
            current
            and current_length + separator_length + len(block)
            > DUPLICATES_DESCRIPTION_LIMIT
        ):
            pages.append("\n\n".join(current))
            current = []
            current_length = 0
        current.append(block)
        current_length += separator_length + len(block)
    if current:
        pages.append("\n\n".join(current))
    return pages or [""]


class DuplicatesView(CreatureListView):
    def __init__(self, author_id: int, pages: list[str]) -> None:
        self.pages = pages
        super().__init__(
            author_id=author_id,
            title="📦 Duplicates",
            entries=pages,
        )
        self.PAGE_SIZE = 1
        self.total_pages = len(pages)
        self._sync_buttons()

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            description=self.pages[self.page],
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages}")
        return embed
