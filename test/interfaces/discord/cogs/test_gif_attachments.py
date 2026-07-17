from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from interfaces.discord import images as images_module
from interfaces.discord.cogs import info as info_module
from interfaces.discord.cogs import ivs_cog as ivs_module
from interfaces.discord.cogs import profile_cog as profile_module
from interfaces.discord.cogs.info import InfoCog
from interfaces.discord.cogs.ivs_cog import IVsCog
from interfaces.discord.cogs.profile_cog import ProfileCog
from interfaces.discord.images import download_gif_file
from rendering.gif_urls import GIF_ASSET_VERSION


@pytest.fixture(autouse=True)
def clear_gif_cache():
    images_module._GIF_CACHE.clear()
    yield
    images_module._GIF_CACHE.clear()


class _DummyNature:
    def arrow_for(self, stat):
        return ""

    def __str__(self):
        return "Hardy"


class _DummyBaseStats:
    def for_stat(self, stat):
        return 50


class _DummySpecies:
    def __init__(
        self,
        name: str = "Pikachu",
        pokeapi_id: int = 25,
    ):
        self.name = name
        self.pokeapi_id = pokeapi_id
        self.types = ["electric"]
        self.height = 4
        self.weight = 60
        self.base_stats = _DummyBaseStats()


class _DummyCreature:
    def __init__(
        self,
        *,
        name: str = "Pikachu",
        pokeapi_id: int = 25,
        collection_number: int = 5,
        shiny: bool = False,
    ):
        self.species = _DummySpecies(
            name=name,
            pokeapi_id=pokeapi_id,
        )
        self.collection_number = collection_number
        self.is_shiny = shiny
        self.size = "M (1.00×)"
        self.nature = _DummyNature()
        self.current_form = None
        self.iv_percentage = 100

    def iv_for(self, stat):
        return 31


class _DummyStatCalculator:
    def calculate(self, creature, stat):
        return 100


def _ctx() -> SimpleNamespace:
    return SimpleNamespace(
        author=SimpleNamespace(
            id=123,
            display_name="Trainer",
            display_avatar=SimpleNamespace(
                url="https://example.invalid/avatar.png",
            ),
        ),
        guild=SimpleNamespace(id=456),
        send=AsyncMock(),
    )


def _core_for_ivs(creature):
    return SimpleNamespace(
        creature_info_service=SimpleNamespace(
            get_creature=AsyncMock(return_value=creature),
        ),
        stat_calculator=_DummyStatCalculator(),
    )


def _core_for_profile(creature):
    return SimpleNamespace(
        profile_service=SimpleNamespace(
            get_profile=AsyncMock(
                return_value=SimpleNamespace(
                    total_captured=1,
                    shiny_count=0,
                    completion_percentage=12.5,
                    unique_species=1,
                    featured_creature=creature,
                ),
            ),
        ),
    )


def _core_for_info(species):
    return SimpleNamespace(
        species_info_service=SimpleNamespace(
            get_species_info=AsyncMock(
                return_value=SimpleNamespace(
                    species=species,
                    creatures=[_DummyCreature()],
                ),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_download_gif_file_seeks_buffer_before_building_discord_file(
    monkeypatch,
) -> None:
    class _Response:
        def __init__(self):
            self.closed = False
            self.content = b"gif-bytes"

        def raise_for_status(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.closed = True

    response = _Response()

    def fake_get(url, timeout, stream):
        assert timeout == 10
        assert stream is True
        return response

    monkeypatch.setattr("interfaces.discord.images.requests.get", fake_get)

    gif_file = await download_gif_file(
        "https://example.invalid/pikachu.gif",
        "pikachu.gif",
    )

    assert isinstance(gif_file, discord.File)
    assert gif_file.filename == "pikachu.gif"
    assert gif_file.fp.tell() == 0
    assert gif_file.fp.read() == b"gif-bytes"
    assert response.closed is True
    assert images_module._GIF_CACHE == {
        "https://example.invalid/pikachu.gif": b"gif-bytes",
    }


@pytest.mark.asyncio
async def test_download_gif_file_uses_cache_on_second_call(monkeypatch) -> None:
    calls: list[str] = []

    class _Response:
        def __init__(self):
            self.content = b"gif-bytes"

        def raise_for_status(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_get(url, timeout, stream):
        calls.append(url)
        return _Response()

    monkeypatch.setattr("interfaces.discord.images.requests.get", fake_get)

    first = await download_gif_file(
        "https://example.invalid/pikachu.gif",
        "first.gif",
    )
    second = await download_gif_file(
        "https://example.invalid/pikachu.gif",
        "second.gif",
    )

    assert calls == ["https://example.invalid/pikachu.gif"]
    assert first.filename == "first.gif"
    assert second.filename == "second.gif"
    assert first.fp.tell() == 0
    assert second.fp.tell() == 0
    assert first.fp.read() == b"gif-bytes"
    assert second.fp.read() == b"gif-bytes"


@pytest.mark.asyncio
async def test_download_gif_file_reuses_bytes_for_distinct_filenames(
    monkeypatch,
) -> None:
    calls: list[str] = []

    class _Response:
        def __init__(self):
            self.content = b"gif-bytes"

        def raise_for_status(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_get(url, timeout, stream):
        calls.append(url)
        return _Response()

    monkeypatch.setattr("interfaces.discord.images.requests.get", fake_get)

    first = await download_gif_file(
        "https://example.invalid/pikachu.gif",
        "ivs.gif",
    )
    second = await download_gif_file(
        "https://example.invalid/pikachu.gif",
        "species.gif",
    )

    assert calls == ["https://example.invalid/pikachu.gif"]
    assert first.filename == "ivs.gif"
    assert second.filename == "species.gif"
    assert first.fp.read() == b"gif-bytes"
    assert second.fp.read() == b"gif-bytes"


@pytest.mark.asyncio
async def test_download_gif_file_evicts_oldest_when_cache_reaches_limit(
    monkeypatch,
) -> None:
    calls: list[str] = []

    class _Response:
        def __init__(self, content: bytes):
            self.content = content

        def raise_for_status(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_get(url, timeout, stream):
        calls.append(url)
        return _Response(url.encode())

    monkeypatch.setattr("interfaces.discord.images.requests.get", fake_get)

    for index in range(images_module._GIF_CACHE_MAX_SIZE + 1):
        await download_gif_file(
            f"https://example.invalid/{index}.gif",
            f"{index}.gif",
        )

    assert len(images_module._GIF_CACHE) == images_module._GIF_CACHE_MAX_SIZE
    assert "https://example.invalid/0.gif" not in images_module._GIF_CACHE
    assert "https://example.invalid/1.gif" in images_module._GIF_CACHE
    assert f"https://example.invalid/{images_module._GIF_CACHE_MAX_SIZE}.gif" in (
        images_module._GIF_CACHE
    )
    assert len(calls) == images_module._GIF_CACHE_MAX_SIZE + 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cog_factory", "module", "core_factory", "filename"),
    [
        (
            ProfileCog,
            profile_module,
            _core_for_profile,
            "profile.gif",
        ),
    ],
)
async def test_gif_commands_attach_remote_image(
    monkeypatch,
    cog_factory,
    module,
    core_factory,
    filename,
) -> None:
    creature = _DummyCreature()
    species = _DummySpecies()

    helper = AsyncMock(
        return_value=discord.File(
            BytesIO(b"gif-bytes"),
            filename=filename,
        ),
    )

    monkeypatch.setattr(module, "download_gif_file", helper)

    core = core_factory(creature if module is not info_module else species)
    ctx = _ctx()

    cog = cog_factory(core)

    if module is ivs_module:
        await IVsCog.ivs.callback(cog, ctx, 7)
    elif module is profile_module:
        await ProfileCog.profile.callback(cog, ctx)
    else:
        await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    ctx.send.assert_awaited_once()
    kwargs = ctx.send.await_args.kwargs

    assert kwargs["file"].filename == filename
    assert kwargs["embed"].image.url == f"attachment://{filename}"
    helper.assert_awaited_once()


@pytest.mark.asyncio
async def test_info_uses_direct_remote_url_without_attachment(monkeypatch) -> None:
    species = _DummySpecies(name="Pikachu", pokeapi_id=25)
    core = _core_for_info(species)
    ctx = _ctx()
    cog = InfoCog(core)
    helper = AsyncMock()

    monkeypatch.setattr(images_module, "download_gif_file", helper)

    await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    ctx.send.assert_awaited_once()
    kwargs = ctx.send.await_args.kwargs
    assert kwargs["content"] == (
        "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev/"
        f"gifs_pokeapi/regular/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert kwargs["embed"] is not None
    assert "image" not in kwargs["embed"].to_dict()
    assert "file" not in kwargs
    helper.assert_not_called()


@pytest.mark.asyncio
async def test_info_does_not_refetch_message_without_debug(monkeypatch) -> None:
    species = _DummySpecies(name="Pikachu", pokeapi_id=25)
    core = _core_for_info(species)
    sent_message = SimpleNamespace(
        id=123,
        channel=SimpleNamespace(fetch_message=AsyncMock()),
    )
    ctx = _ctx()
    ctx.send = AsyncMock(return_value=sent_message)
    cog = InfoCog(core)

    monkeypatch.delenv("GIF_PROXY_DEBUG", raising=False)

    await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    sent_message.channel.fetch_message.assert_not_called()


@pytest.mark.asyncio
async def test_info_refetches_message_and_logs_proxy_metadata_when_debug_enabled(
    monkeypatch,
    caplog,
) -> None:
    species = _DummySpecies(name="Pikachu", pokeapi_id=25)
    core = _core_for_info(species)
    fetched_embed = SimpleNamespace(
        image=SimpleNamespace(
            url="https://example.invalid/original.gif",
            proxy_url="https://example.invalid/proxy.gif",
            width=240,
            height=240,
        )
    )
    sent_message = SimpleNamespace(
        id=123,
        channel=SimpleNamespace(
            fetch_message=AsyncMock(
                return_value=SimpleNamespace(embeds=[fetched_embed])
            ),
        ),
    )
    ctx = _ctx()
    ctx.send = AsyncMock(return_value=sent_message)
    cog = InfoCog(core)

    monkeypatch.setenv("GIF_PROXY_DEBUG", "true")
    caplog.set_level("INFO", logger=info_module.logger.name)

    await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    sent_message.channel.fetch_message.assert_awaited_once_with(sent_message.id)
    assert "info_gif_proxy_debug enabled" in caplog.text
    assert "info_gif_proxy_debug message_sent" in caplog.text
    assert "info_gif_proxy_debug" in caplog.text
    assert "fetched url=https://example.invalid/original.gif" in caplog.text
    assert "proxy_url=https://example.invalid/proxy.gif" in caplog.text
    assert "width=240" in caplog.text
    assert "height=240" in caplog.text


@pytest.mark.asyncio
async def test_info_debug_fetch_failure_does_not_break_response(monkeypatch) -> None:
    species = _DummySpecies(name="Pikachu", pokeapi_id=25)
    core = _core_for_info(species)
    sent_message = SimpleNamespace(
        id=123,
        channel=SimpleNamespace(
            fetch_message=AsyncMock(side_effect=RuntimeError("discord down"))
        ),
    )
    ctx = _ctx()
    ctx.send = AsyncMock(return_value=sent_message)
    cog = InfoCog(core)

    monkeypatch.setenv("GIF_PROXY_DEBUG", "true")

    await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    ctx.send.assert_awaited_once()
    sent_message.channel.fetch_message.assert_awaited_once_with(sent_message.id)


@pytest.mark.asyncio
async def test_info_debug_fetch_failure_logs_failure_type(
    monkeypatch,
    caplog,
) -> None:
    species = _DummySpecies(name="Pikachu", pokeapi_id=25)
    core = _core_for_info(species)
    sent_message = SimpleNamespace(
        id=123,
        channel=SimpleNamespace(
            fetch_message=AsyncMock(side_effect=RuntimeError("discord down"))
        ),
    )
    ctx = _ctx()
    ctx.send = AsyncMock(return_value=sent_message)
    cog = InfoCog(core)

    monkeypatch.setenv("GIF_PROXY_DEBUG", "1")
    caplog.set_level("INFO", logger=info_module.logger.name)

    await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    assert "info_gif_proxy_debug enabled" in caplog.text
    assert "info_gif_proxy_debug message_sent" in caplog.text
    assert "info_gif_proxy_debug fetch_failed error_type=RuntimeError" in caplog.text
    ctx.send.assert_awaited_once()
    sent_message.channel.fetch_message.assert_awaited_once_with(sent_message.id)


@pytest.mark.parametrize("env_value", ["true", "TRUE", "1"])
def test_info_gif_proxy_debug_env_values_activate_instrumentation(
    monkeypatch, env_value
) -> None:
    from interfaces.discord.cogs.info import _gif_proxy_debug_enabled

    monkeypatch.setenv("GIF_PROXY_DEBUG", env_value)

    assert _gif_proxy_debug_enabled() is True


@pytest.mark.asyncio
async def test_ivs_uses_direct_remote_url_without_attachment(monkeypatch) -> None:
    creature = _DummyCreature()
    core = _core_for_ivs(creature)
    ctx = _ctx()
    cog = IVsCog(core)
    helper = AsyncMock()

    monkeypatch.setattr(images_module, "download_gif_file", helper)

    await IVsCog.ivs.callback(cog, ctx, 7)

    ctx.send.assert_awaited_once()
    kwargs = ctx.send.await_args.kwargs
    assert kwargs["embed"].image.url == (
        "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev/"
        f"gifs_pokeapi/regular/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert "file" not in kwargs
    assert "attachment://" not in kwargs["embed"].image.url
    helper.assert_not_called()


@pytest.mark.asyncio
async def test_profile_still_uses_attachment(monkeypatch) -> None:
    creature = _DummyCreature()
    core = _core_for_profile(creature)
    ctx = _ctx()
    cog = ProfileCog(core)
    helper = AsyncMock(
        return_value=discord.File(BytesIO(b"gif-bytes"), filename="profile.gif")
    )

    monkeypatch.setattr(profile_module, "download_gif_file", helper)

    await ProfileCog.profile.callback(cog, ctx)

    ctx.send.assert_awaited()
    kwargs = ctx.send.await_args.kwargs
    assert kwargs["embed"] is not None
    assert kwargs["file"].filename == "profile.gif"
    assert kwargs["embed"].image.url == "attachment://profile.gif"
    helper.assert_awaited_once()


@pytest.mark.asyncio
async def test_versioned_urls_produce_distinct_cache_entries(monkeypatch) -> None:
    calls: list[str] = []

    class _Response:
        def __init__(self, content: bytes):
            self.content = content

        def raise_for_status(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_get(url, timeout, stream):
        calls.append(url)
        return _Response(url.encode())

    monkeypatch.setattr("interfaces.discord.images.requests.get", fake_get)
    images_module._GIF_CACHE.clear()

    first = await download_gif_file(
        "https://example.invalid/pikachu.gif?v=20260717-1",
        "first.gif",
    )
    second = await download_gif_file(
        "https://example.invalid/pikachu.gif?v=20260717-2",
        "second.gif",
    )

    assert calls == [
        "https://example.invalid/pikachu.gif?v=20260717-1",
        "https://example.invalid/pikachu.gif?v=20260717-2",
    ]
    assert first.filename == "first.gif"
    assert second.filename == "second.gif"
    assert len(images_module._GIF_CACHE) == 2
    assert (
        "https://example.invalid/pikachu.gif?v=20260717-1" in images_module._GIF_CACHE
    )
    assert (
        "https://example.invalid/pikachu.gif?v=20260717-2" in images_module._GIF_CACHE
    )
