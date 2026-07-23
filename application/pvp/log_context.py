from __future__ import annotations

import re
import traceback
from collections.abc import Mapping

LOG_CONTEXT_FIELDS = (
    "session_id",
    "guild_id",
    "channel_id",
    "player1_id",
    "player2_id",
)


def safe_traceback(error: BaseException) -> str:
    text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    text = re.sub(
        r"(?i)(authorization|password|secret|token)(\s*[:=]\s*)\S+",
        r"\1\2[REDACTED]",
        text,
    )
    return text[:4000]


def safe_error_message(error: BaseException) -> str:
    text = re.sub(
        r"(?i)(authorization|password|secret|token)(\s*[:=]\s*)\S+",
        r"\1\2[REDACTED]",
        str(error),
    )
    return text[:500]


def format_pvp_context(context: Mapping[str, object]) -> str:
    return " ".join(
        f"{field}={context.get(field, '-')}" for field in LOG_CONTEXT_FIELDS
    )


def session_log_context(
    session, *, guild_id=None, channel_id=None
) -> dict[str, object]:
    return {
        "session_id": str(session.id),
        "guild_id": guild_id if guild_id is not None else "-",
        "channel_id": channel_id if channel_id is not None else "-",
        "player1_id": session.initiator_id,
        "player2_id": session.opponent_id,
    }
