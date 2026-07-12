from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from interfaces.discord.cogs import info as info_module
from interfaces.discord.cogs import ivs_cog as ivs_module
from interfaces.discord.cogs import profile_cog as profile_module
from interfaces.discord.cogs.info import InfoCog
from interfaces.discord.cogs.ivs_cog import IVsCog
from interfaces.discord.cogs.profile_cog import ProfileCog
from interfaces.discord.images import download_gif_file


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cog_factory", "module", "core_factory", "filename"),
    [
        (
            IVsCog,
            ivs_module,
            _core_for_ivs,
            "ivs.gif",
        ),
        (
            ProfileCog,
            profile_module,
            _core_for_profile,
            "profile.gif",
        ),
        (
            InfoCog,
            info_module,
            _core_for_info,
            "species.gif",
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
@pytest.mark.parametrize(
    ("cog_factory", "module", "core_factory", "warning"),
    [
        (
            IVsCog,
            ivs_module,
            _core_for_ivs,
            "Unable to attach creature GIF command=ivs species=Pikachu",
        ),
        (
            ProfileCog,
            profile_module,
            _core_for_profile,
            "Unable to attach creature GIF command=profile species=Pikachu",
        ),
        (
            InfoCog,
            info_module,
            _core_for_info,
            "Unable to attach species GIF command=info species=Pikachu",
        ),
    ],
)
async def test_gif_commands_fall_back_without_attachment(
    monkeypatch,
    caplog,
    cog_factory,
    module,
    core_factory,
    warning,
) -> None:
    async def failing_helper(url, attachment_name):
        raise RuntimeError("download failed")

    monkeypatch.setattr(module, "download_gif_file", failing_helper)

    creature = _DummyCreature()
    species = _DummySpecies()
    core = core_factory(creature if module is not info_module else species)
    ctx = _ctx()
    cog = cog_factory(core)

    caplog.clear()

    if module is ivs_module:
        await IVsCog.ivs.callback(cog, ctx, 7)
    elif module is profile_module:
        await ProfileCog.profile.callback(cog, ctx)
    else:
        await InfoCog.info.callback(cog, ctx, pokemon="pikachu")

    ctx.send.assert_awaited_once()
    kwargs = ctx.send.await_args.kwargs

    assert "file" not in kwargs
    assert kwargs["embed"] is not None
    assert warning in caplog.text
    assert "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev" not in caplog.text
