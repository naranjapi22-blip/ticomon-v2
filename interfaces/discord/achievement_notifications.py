import logging

from application.achievement.query_service import ACHIEVEMENT_PRESENTATION

logger = logging.getLogger(__name__)


def _display_name(achievement_id: str) -> str:
    return ACHIEVEMENT_PRESENTATION.get(achievement_id, (achievement_id,))[0]


def format_unlocks(unlocks) -> str:
    return "\n".join(
        "Achievement unlocked: "
        f"{_display_name(unlock.achievement_id)} — "
        + ", ".join(
            f"{kind.value.title()} Candy +{amount}"
            for kind, amount in unlock.rewarded_candies.items()
        )
        + (f", Nature Mint +{unlock.rewarded_mints}" if unlock.rewarded_mints else "")
        for unlock in unlocks
    )


async def send_unlocks(send, unlocks, *, context: str) -> None:
    if not unlocks:
        return
    try:
        await send(format_unlocks(unlocks))
    except Exception:
        logger.exception("achievement notification failed context=%s", context)
