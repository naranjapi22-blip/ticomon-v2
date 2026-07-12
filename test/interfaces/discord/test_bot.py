import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from discord.ext import commands

from interfaces.discord.bot import TicoMonBot
from interfaces.discord.cogs.trade_cog import TradeCog


@pytest.mark.asyncio
async def test_setup_hook_registers_trade_cog() -> None:
    bot = TicoMonBot()
    bot.add_cog = AsyncMock()

    await bot.setup_hook()

    assert any(
        isinstance(call.args[0], TradeCog) for call in bot.add_cog.await_args_list
    )


def _build_context(
    *,
    command=None,
    cog=None,
):
    return SimpleNamespace(
        command=command,
        cog=cog,
        guild=SimpleNamespace(id=111),
        channel=SimpleNamespace(id=222),
        author=SimpleNamespace(id=333),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error",),
    [
        (commands.CommandNotFound("unknown command"),),
        (
            commands.MissingRequiredArgument(
                SimpleNamespace(
                    displayed_name=None,
                    name="collection_number",
                )
            ),
        ),
        (commands.BadArgument("bad argument"),),
        (commands.CheckFailure("check failure"),),
    ],
)
async def test_on_command_error_ignores_expected_errors(
    error,
    caplog,
) -> None:
    caplog.set_level(logging.ERROR)
    bot = TicoMonBot()
    ctx = _build_context(
        command=SimpleNamespace(
            qualified_name="trade",
            has_error_handler=lambda: False,
        ),
        cog=None,
    )

    await bot.on_command_error(ctx, error)

    assert caplog.records == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("local_handler_factory",),
    [
        (
            lambda: _build_context(
                command=SimpleNamespace(
                    qualified_name="trade",
                    has_error_handler=lambda: True,
                ),
                cog=None,
            ),
        ),
        (
            lambda: _build_context(
                command=SimpleNamespace(
                    qualified_name="trade",
                    has_error_handler=lambda: False,
                ),
                cog=SimpleNamespace(has_error_handler=lambda: True),
            ),
        ),
    ],
)
async def test_on_command_error_ignores_local_handlers(
    local_handler_factory,
    caplog,
) -> None:
    caplog.set_level(logging.ERROR)
    bot = TicoMonBot()
    ctx = local_handler_factory()

    await bot.on_command_error(
        ctx,
        commands.CommandInvokeError(RuntimeError("boom")),
    )

    assert caplog.records == []


@pytest.mark.asyncio
async def test_on_command_error_logs_command_invoke_error_once(caplog) -> None:
    caplog.set_level(logging.ERROR)
    bot = TicoMonBot()
    ctx = _build_context(
        command=SimpleNamespace(
            qualified_name="trade accept",
            has_error_handler=lambda: False,
        ),
        cog=None,
    )

    try:
        raise ValueError("boom")
    except ValueError as original:
        await bot.on_command_error(
            ctx,
            commands.CommandInvokeError(original),
        )

    errors = [record for record in caplog.records if record.levelno == logging.ERROR]

    assert len(errors) == 1

    record = errors[0]

    assert (
        record.getMessage()
        == "Unhandled command error command=trade accept guild=111 channel=222 user=333"
    )
    assert record.exc_info is not None
    assert record.exc_info[0] is ValueError
    assert str(record.exc_info[1]) == "boom"
    assert record.exc_info[2] is not None


@pytest.mark.asyncio
async def test_on_command_error_logs_unexpected_command_error_once(caplog) -> None:
    caplog.set_level(logging.ERROR)
    bot = TicoMonBot()
    ctx = _build_context(
        command=SimpleNamespace(
            qualified_name="trade",
            has_error_handler=lambda: False,
        ),
        cog=None,
    )

    try:
        raise commands.CommandError("framework failure")
    except commands.CommandError as error:
        await bot.on_command_error(
            ctx,
            error,
        )

    errors = [record for record in caplog.records if record.levelno == logging.ERROR]

    assert len(errors) == 1

    record = errors[0]

    assert record.getMessage() == (
        "Unhandled command framework error command=trade guild=111 "
        "channel=222 user=333 error_type=CommandError"
    )
    assert record.exc_info is not None
    assert record.exc_info[0] is commands.CommandError
    assert str(record.exc_info[1]) == "framework failure"
    assert record.exc_info[2] is not None


@pytest.mark.asyncio
async def test_on_error_logs_event_exception_with_traceback(caplog) -> None:
    caplog.set_level(logging.ERROR)
    bot = TicoMonBot()

    try:
        raise RuntimeError("event boom")
    except RuntimeError:
        await bot.on_error(
            "on_message",
            SimpleNamespace(payload="sensitive"),
            secret="value",
        )

    errors = [record for record in caplog.records if record.levelno == logging.ERROR]

    assert len(errors) == 1

    record = errors[0]

    assert record.getMessage() == "Unhandled Discord event error event=on_message"
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError
    assert str(record.exc_info[1]) == "event boom"
    assert record.exc_info[2] is not None
    assert "sensitive" not in record.getMessage()
    assert "secret" not in record.getMessage()
