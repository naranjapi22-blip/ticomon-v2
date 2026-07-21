import asyncio
import logging
import re
from types import SimpleNamespace

import pytest

import infrastructure.battle.poke_env.pvp_controller as controller_module
from application.pvp.pvp_application_service import PvpApplicationService
from core.pvp.session import PvpSessionRegistry
from core.team.team_slot import TeamSlot
from infrastructure.battle.poke_env.pvp_controller import (
    PokeEnvPvpController,
    PvpControllerCallbacks,
    _PvpClientLogger,
    _RetrievedTaskSet,
)


class TeamRepository:
    def __init__(self, creatures):
        self.slots = {
            trainer_id: [
                TeamSlot(trainer_id, index, creature.id, index)
                for index, creature in enumerate(team, start=1)
            ]
            for trainer_id, team in creatures.items()
        }

    async def get_by_trainer(self, trainer_id):
        return list(self.slots.get(trainer_id, ()))


class CreatureRepository:
    def __init__(self, creatures):
        self.creatures = {
            creature.id: creature for team in creatures.values() for creature in team
        }

    async def get_many(self, creature_ids):
        return [self.creatures[creature_id] for creature_id in creature_ids]

    async def get_by_collection_number(self, trainer_id, collection_number):
        return next(
            creature
            for creature in self.creatures.values()
            if creature.trainer_id == trainer_id
            and creature.collection_number == collection_number
        )


class Validator:
    def validate_creature(self, creature):
        if not creature.eligible:
            raise ValueError("invalid loadout")
        return creature

    def validate(self, creatures):
        return tuple(self.validate_creature(creature) for creature in creatures)


def _creatures():
    result = {}
    for trainer_id, offset in ((1, 0), (2, 10)):
        result[trainer_id] = [
            SimpleNamespace(
                id=offset + index,
                trainer_id=trainer_id,
                collection_number=offset + index,
                eligible=True,
                is_shiny=False,
                species=SimpleNamespace(id=offset + index, name=f"Species{index}"),
            )
            for index in range(1, 4)
        ]
    return result


@pytest.mark.asyncio
async def test_pvp_selector_uses_only_configured_team_and_filters_invalid_loadouts():
    creatures = _creatures()
    collection_creature = SimpleNamespace(
        id=99,
        trainer_id=1,
        collection_number=99,
        eligible=True,
        is_shiny=False,
        species=SimpleNamespace(id=99, name="CollectionOnly"),
    )
    creatures[1].append(collection_creature)
    team_repository = TeamRepository({1: creatures[1][:3], 2: creatures[2]})
    repository = CreatureRepository(creatures)
    service = PvpApplicationService(
        registry=PvpSessionRegistry(),
        creature_repository=repository,
        team_repository=team_repository,
        team_validator=Validator(),
    )

    options = await service.get_team_selector(1)

    assert [number for number, _ in options] == [1, 2, 3]
    assert 99 not in [number for number, _ in options]


@pytest.mark.asyncio
async def test_selector_returns_fewer_than_three_when_team_is_not_eligible():
    creatures = _creatures()
    creatures[1][2].eligible = False
    service = PvpApplicationService(
        registry=PvpSessionRegistry(),
        creature_repository=CreatureRepository(creatures),
        team_repository=TeamRepository(creatures),
        team_validator=Validator(),
    )

    options = await service.get_team_selector(1)

    assert len(options) == 2


@pytest.mark.asyncio
async def test_confirmation_revalidates_creatures_removed_from_team():
    creatures = _creatures()
    teams = TeamRepository(creatures)
    service = PvpApplicationService(
        registry=PvpSessionRegistry(),
        creature_repository=CreatureRepository(creatures),
        team_repository=teams,
        team_validator=Validator(),
        controller_factory=lambda: SimpleNamespace(),
    )
    session = service.challenge(1, 2)
    await service.select_team(session.id, 1, [1, 2, 3])
    await service.select_team(session.id, 2, [11, 12, 13])
    assert not await service.confirm_team(session.id, 1)
    teams.slots[2].pop()

    with pytest.raises(ValueError, match="no longer in the trainer's team"):
        await service.confirm_team(session.id, 2)


@pytest.mark.asyncio
async def test_simultaneous_confirmations_start_one_controller():
    creatures = _creatures()
    starts = 0

    class Controller:
        async def start(self, teams, callbacks):
            nonlocal starts
            starts += 1
            await asyncio.sleep(0)

        async def close(self):
            return

    service = PvpApplicationService(
        registry=PvpSessionRegistry(),
        creature_repository=CreatureRepository(creatures),
        team_repository=TeamRepository(creatures),
        team_validator=Validator(),
        controller_factory=Controller,
    )
    session = service.challenge(1, 2)
    await service.select_team(session.id, 1, [1, 2, 3])
    await service.select_team(session.id, 2, [11, 12, 13])

    results = await asyncio.gather(
        service.confirm_team(session.id, 1), service.confirm_team(session.id, 2)
    )
    await asyncio.sleep(0)

    assert sorted(results) == [False, True]
    assert starts == 1
    await service.cleanup(session.id)


@pytest.mark.asyncio
async def test_start_failure_cleans_session_and_releases_trainers(caplog):
    creatures = _creatures()
    closed = 0

    class FailingController:
        async def start(self, teams, callbacks):
            raise TimeoutError("login timeout token=secret-value")

        async def close(self):
            nonlocal closed
            closed += 1

    service = PvpApplicationService(
        registry=PvpSessionRegistry(),
        creature_repository=CreatureRepository(creatures),
        team_repository=TeamRepository(creatures),
        team_validator=Validator(),
        controller_factory=FailingController,
    )
    session = service.challenge(1, 2)
    await service.select_team(session.id, 1, [1, 2, 3])
    await service.select_team(session.id, 2, [11, 12, 13])
    assert not await service.confirm_team(session.id, 1)
    assert await service.confirm_team(session.id, 2)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    with pytest.raises(ValueError):
        service.registry.get(session.id)
    assert not service.registry.is_occupied(1)
    assert not service.registry.is_occupied(2)
    assert closed == 1
    startup_records = [
        record
        for record in caplog.records
        if record.message.startswith("PvP startup failed")
    ]
    assert len(startup_records) == 1
    assert str(session.id) in startup_records[0].message
    assert "phase=starting" in startup_records[0].message
    assert "TimeoutError" in startup_records[0].message
    assert "login timeout" in startup_records[0].message
    assert "secret-value" not in startup_records[0].message
    assert "token=[REDACTED]" in startup_records[0].message
    assert startup_records[0].exc_info is not None


class FakePlayer:
    created = []

    def __init__(self, trainer_id, team, username, callback_tasks, **kwargs):
        self.trainer_id = trainer_id
        self.username = username
        self.server_configuration = kwargs["server_configuration"]
        self.ps_client = SimpleNamespace(
            logged_in=asyncio.Event(),
            stop_listening=self._stop_listening,
            _active_tasks=set(),
        )
        self.battles = {}
        self.ps_client.logged_in.set()
        self.__class__.created.append(self)

    async def _stop_listening(self):
        return

    async def battle_against(self, opponent):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_showdown_usernames_are_unique_valid_and_side_specific(monkeypatch):
    FakePlayer.created = []
    monkeypatch.setattr(
        controller_module,
        "SHOWDOWN_WEBSOCKET_URL",
        "ws://showdown.internal/showdown/websocket",
    )
    monkeypatch.setattr(
        controller_module,
        "SHOWDOWN_AUTHENTICATION_URL",
        "http://showdown.internal/action.php?",
    )
    controller = PokeEnvPvpController(
        player_factory=FakePlayer, session_token="0123456789abcdef"
    )
    controller._pack_team = lambda team: ""
    callbacks = PvpControllerCallbacks(
        on_actions=lambda *_: asyncio.sleep(0),
        on_protocol=lambda *_: asyncio.sleep(0),
        on_finished=lambda *_: asyncio.sleep(0),
    )

    await controller.start({1: (), 2: ()}, callbacks)
    names = [player.username for player in FakePlayer.created]

    assert names[0] != names[1]
    assert len(set(names)) == 2
    assert all(len(name) <= 18 and re.fullmatch(r"[a-z0-9]+", name) for name in names)
    await controller.close()


@pytest.mark.asyncio
async def test_railway_showdown_url_reaches_server_configuration(monkeypatch):
    railway_url = "ws://pokemon-showdown.railway.internal:8080/showdown/websocket"
    FakePlayer.created = []
    monkeypatch.setenv("SHOWDOWN_WEBSOCKET_URL", railway_url)
    monkeypatch.delenv("SHOWDOWN_AUTHENTICATION_URL", raising=False)
    controller = PokeEnvPvpController(player_factory=FakePlayer)
    controller._pack_team = lambda team: ""
    callbacks = PvpControllerCallbacks(
        on_actions=lambda *_: asyncio.sleep(0),
        on_protocol=lambda *_: asyncio.sleep(0),
        on_finished=lambda *_: asyncio.sleep(0),
    )

    await controller.start({1: (), 2: ()}, callbacks)

    assert len(FakePlayer.created) == 2
    assert all(
        player.server_configuration.websocket_url == railway_url
        for player in FakePlayer.created
    )
    assert all(
        player.server_configuration.authentication_url == ""
        for player in FakePlayer.created
    )
    await controller.close()


@pytest.mark.asyncio
async def test_showdown_login_retry_is_limited(monkeypatch):
    FakePlayer.created = []
    monkeypatch.setattr(
        controller_module,
        "SHOWDOWN_WEBSOCKET_URL",
        "ws://showdown.internal/showdown/websocket",
    )
    monkeypatch.setattr(
        controller_module,
        "SHOWDOWN_AUTHENTICATION_URL",
        "http://showdown.internal/action.php?",
    )
    monkeypatch.setattr(controller_module, "SHOWDOWN_CONNECTION_TIMEOUT_SECONDS", 0.001)
    for player in FakePlayer.created:
        player.ps_client.logged_in.clear()
    original_init = FakePlayer.__init__

    def never_login(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.ps_client.logged_in.clear()

    monkeypatch.setattr(FakePlayer, "__init__", never_login)
    controller = PokeEnvPvpController(player_factory=FakePlayer)
    controller._pack_team = lambda team: ""
    callbacks = PvpControllerCallbacks(
        on_actions=lambda *_: asyncio.sleep(0),
        on_protocol=lambda *_: asyncio.sleep(0),
        on_finished=lambda *_: asyncio.sleep(0),
    )

    with pytest.raises(TimeoutError):
        await controller.start({1: (), 2: ()}, callbacks)

    assert len(FakePlayer.created) == 6


def test_implicit_local_showdown_defaults_are_rejected(monkeypatch):
    monkeypatch.delenv("SHOWDOWN_WEBSOCKET_URL", raising=False)
    monkeypatch.delenv("SHOWDOWN_AUTHENTICATION_URL", raising=False)
    monkeypatch.setattr(
        controller_module,
        "SHOWDOWN_WEBSOCKET_URL",
        controller_module.DEFAULT_SHOWDOWN_WEBSOCKET_URL,
    )
    monkeypatch.setattr(
        controller_module,
        "SHOWDOWN_AUTHENTICATION_URL",
        "",
    )

    with pytest.raises(RuntimeError, match="default localhost URLs"):
        controller_module.validate_showdown_configuration()


def test_explicit_localhost_is_accepted_for_development(monkeypatch):
    monkeypatch.setenv(
        "SHOWDOWN_WEBSOCKET_URL", "ws://localhost:8000/showdown/websocket"
    )
    monkeypatch.delenv("SHOWDOWN_AUTHENTICATION_URL", raising=False)

    assert controller_module.validate_showdown_configuration() == (
        "ws://localhost:8000/showdown/websocket",
        "",
    )


def test_explicit_showdown_urls_are_accepted(monkeypatch):
    monkeypatch.setenv(
        "SHOWDOWN_WEBSOCKET_URL", "wss://showdown.internal/showdown/websocket"
    )
    monkeypatch.setenv(
        "SHOWDOWN_AUTHENTICATION_URL", "https://showdown.internal/action.php?"
    )

    assert controller_module.validate_showdown_configuration() == (
        "wss://showdown.internal/showdown/websocket",
        "https://showdown.internal/action.php?",
    )


@pytest.mark.parametrize(
    "websocket_url,expected",
    [
        ("http://showdown.internal/showdown/websocket", "must use ws or wss"),
        ("ws:///showdown/websocket", "must include a hostname"),
    ],
)
def test_invalid_showdown_websocket_urls_are_rejected(
    monkeypatch, websocket_url, expected
):
    monkeypatch.setenv("SHOWDOWN_WEBSOCKET_URL", websocket_url)
    monkeypatch.delenv("SHOWDOWN_AUTHENTICATION_URL", raising=False)

    with pytest.raises(RuntimeError, match=expected):
        controller_module.validate_showdown_configuration()


@pytest.mark.asyncio
async def test_background_task_exception_is_retrieved():
    player = SimpleNamespace(background_errors=[])
    player._record_background_error = player.background_errors.append
    tasks = _RetrievedTaskSet(player)

    async def fail():
        raise RuntimeError("controlled")

    task = asyncio.create_task(fail())
    tasks.add(task)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert isinstance(player.background_errors[0], RuntimeError)


def test_intentional_client_cancellation_is_debug_not_critical(caplog):
    base_logger = logging.getLogger("test.pvp.client")
    adapter = _PvpClientLogger(base_logger, lambda: True)

    with caplog.at_level(logging.DEBUG, logger="test.pvp.client"):
        adapter.critical("CancelledError intercepted: %s", "cleanup")

    assert "CancelledError intercepted" in caplog.text
    assert not [
        record for record in caplog.records if record.levelno >= logging.CRITICAL
    ]


def test_unexpected_client_cancellation_remains_an_error(caplog):
    base_logger = logging.getLogger("test.pvp.active-client")
    adapter = _PvpClientLogger(base_logger, lambda: False)

    with caplog.at_level(logging.CRITICAL, logger="test.pvp.active-client"):
        adapter.critical("CancelledError intercepted: %s", "active battle")

    assert any(record.levelno >= logging.CRITICAL for record in caplog.records)
