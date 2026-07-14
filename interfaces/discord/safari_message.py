from __future__ import annotations

import logging

import discord

from application.bootstrap.core import CoreServices

logger = logging.getLogger(__name__)


async def clear_active_safari_message(
    core: CoreServices,
    guild_id: int,
) -> None:
    tracker = getattr(core, "safari_activity_tracker", None)
    if tracker is None:
        return
    tracker.clear_message(guild_id)


async def delete_active_safari_message(
    core: CoreServices,
    guild_id: int,
    channel: discord.abc.Messageable,
) -> None:
    tracker = getattr(core, "safari_activity_tracker", None)
    if tracker is None:
        return

    snapshot = tracker.get_message(guild_id)
    message_id = snapshot.message_id
    if message_id is None or not isinstance(message_id, int):
        return

    messageable = getattr(channel, "channel", channel)
    channel_id = getattr(messageable, "id", None)
    if (
        snapshot.channel_id is not None
        and isinstance(snapshot.channel_id, int)
        and isinstance(channel_id, int)
    ):
        if snapshot.channel_id != channel_id:
            return

    fetch_message = getattr(messageable, "fetch_message", None)
    try:
        if fetch_message is not None:
            message = await fetch_message(message_id)
            await message.delete()
    except discord.NotFound:
        pass
    except Exception:
        logger.exception(
            "safari_active_message_delete_failed guild_id=%s message_id=%s",
            guild_id,
            message_id,
        )
    finally:
        tracker.clear_message(guild_id)


async def remember_active_safari_message(
    core: CoreServices,
    guild_id: int,
    message: discord.Message,
) -> None:
    tracker = getattr(core, "safari_activity_tracker", None)
    if tracker is None:
        return
    channel_id = getattr(message.channel, "id", None)
    message_id = getattr(message, "id", None)
    if not isinstance(channel_id, int) or not isinstance(message_id, int):
        return
    tracker.set_message(guild_id, channel_id, message_id)
