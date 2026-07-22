import logging

from application.achievement.query_service import ACHIEVEMENT_PRESENTATION
from interfaces.discord.application_emojis import (
    candy_emoji_prefix,
    get_application_emojis,
)

logger = logging.getLogger(__name__)


def format_mint_reward(amount: int) -> str:
    label = "Nature Mint" if amount == 1 else "Nature Mints"
    return f"{label} +{amount}"


def _display_name(achievement_id: str) -> str:
    return ACHIEVEMENT_PRESENTATION.get(achievement_id, (achievement_id,))[0]


def _format_candy_reward(kind, amount, emoji_index) -> str:
    return (
        f"{candy_emoji_prefix(emoji_index or {}, kind)}"
        f"{kind.value.title()} Candy +{amount}"
    )


def format_unlocks(unlocks, emoji_index=None) -> str:
    return "\n".join(
        "Achievement unlocked: "
        f"{_display_name(unlock.achievement_id)} — "
        + ", ".join(
            _format_candy_reward(kind, amount, emoji_index)
            for kind, amount in unlock.rewarded_candies.items()
        )
        + (
            f", {format_mint_reward(unlock.rewarded_mints)}"
            if unlock.rewarded_mints
            else ""
        )
        for unlock in unlocks
    )


async def send_unlocks(send, unlocks, *, context: str, bot=None) -> None:
    if not unlocks:
        return
    try:
        emoji_index = await get_application_emojis(bot) if bot is not None else {}
        await send(format_unlocks(unlocks, emoji_index))
    except Exception:
        logger.exception("achievement notification failed context=%s", context)
