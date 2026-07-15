import logging

logger = logging.getLogger(__name__)


def format_unlocks(unlocks) -> str:
    return "\n".join(
        "Achievement unlocked: "
        f"{unlock.achievement_id} — "
        + ", ".join(
            f"{kind.value.title()} Candy +{amount}"
            for kind, amount in unlock.rewarded_candies.items()
        )
        for unlock in unlocks
    )


async def send_unlocks(send, unlocks, *, context: str) -> None:
    if not unlocks:
        return
    try:
        await send(format_unlocks(unlocks))
    except Exception:
        logger.exception("achievement notification failed context=%s", context)
