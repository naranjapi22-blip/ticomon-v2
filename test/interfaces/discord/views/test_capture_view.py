from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.views.capture_view import CaptureView


@pytest.mark.asyncio
async def test_capture_view_timeout_preserves_the_spawn_gif_attachment() -> None:
    view = CaptureView(SimpleNamespace())
    message = SimpleNamespace(edit=AsyncMock())
    view.message = message

    await view.on_timeout()

    assert all(item.disabled for item in view.children)
    message.edit.assert_awaited_once_with(view=view)
