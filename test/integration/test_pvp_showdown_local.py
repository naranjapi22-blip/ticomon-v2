from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

import pytest

from scripts.diagnose_pvp_showdown import run_diagnostic


def _local_showdown_available() -> bool:
    url = os.getenv("SHOWDOWN_WEBSOCKET_URL", "ws://localhost:8000/showdown/websocket")
    parsed = urlparse(url)
    if parsed.hostname is None or parsed.port is None:
        return False

    host = "127.0.0.1" if parsed.hostname == "localhost" else parsed.hostname

    async def probe() -> None:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, parsed.port), timeout=1
        )
        writer.close()
        await writer.wait_closed()

    try:
        asyncio.run(probe())
    except (OSError, asyncio.TimeoutError):
        return False
    return True


@pytest.mark.showdown_local
def test_two_manual_players_complete_a_local_showdown_battle() -> None:
    if not _local_showdown_available():
        pytest.skip("A local Showdown WebSocket server is not available.")

    result = asyncio.run(run_diagnostic())

    assert result.snapshots
    assert result.battle_finished
    assert any(snapshot.finished for snapshot in result.snapshots)
