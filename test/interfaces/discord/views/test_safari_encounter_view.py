from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from application.safari import ResolveSafariCaptureResult
from application.safari.activity_state import SafariActivityTracker
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import SafariComposition, SafariSessionStatus, SafariThematicEvent
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from interfaces.discord.buttons.pokedex_button import PokedexButton
from interfaces.discord.views.safari_encounter_view import (
    SafariBallCountView,
    SafariEncounterView,
)
from interfaces.discord.views.safari_route_view import SafariRouteView
from test.factories import create_species
from test.unit.safari.test_session import make_encounter, make_session, make_vote


def _encounter_view(
    remaining_encounters: int = 2,
) -> tuple[SafariEncounterView, object]:
    session = make_session()
    session._route_segments[0].remaining_encounters = remaining_encounters
    encounter = make_encounter((25, 26))
    session.publish_encounter(encounter)
    view = SafariEncounterView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
    )
    view.message = AsyncMock()
    return view, session


@pytest.mark.asyncio
async def test_encounter_view_builds_attachment_message_and_pokedex_button() -> None:
    view, _ = _encounter_view()

    content, file = await view.build_message()

    assert content.startswith("Safari Encounter")
    assert "Choose a Pokémon and the number of Safari Balls." in content
    assert "Resolves in 30 seconds." in content
    assert file.filename == "safari-encounter.png"
    assert [child.__class__.__name__ for child in view.children] == [
        "SafariEncounterSlotSelect",
        "PokedexButton",
    ]
    assert any(isinstance(child, PokedexButton) for child in view.children)


def test_encounter_slot_selector_labels_show_only_species_names() -> None:
    session = make_session()
    encounter = SafariEncounter(
        id=uuid4(),
        composition=SafariComposition.NORMAL,
        slots=(
            SafariEncounterSlot(
                uuid4(),
                OpportunityFactory.create(create_species(id=162, name="Furret")),
            ),
            SafariEncounterSlot(
                uuid4(),
                OpportunityFactory.create(create_species(id=951, name="Klawf")),
            ),
            SafariEncounterSlot(
                uuid4(),
                OpportunityFactory.create(create_species(id=327, name="Spinda")),
            ),
        ),
    )
    session.publish_encounter(encounter)
    view = SafariEncounterView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
    )

    selector = view.children[0]
    assert [option.label for option in selector.options] == [
        "Furret",
        "Klawf",
        "Spinda",
    ]
    assert all(not option.label.startswith("Slot") for option in selector.options)
    assert [option.value for option in selector.options] == [
        str(slot.id) for slot in encounter.slots
    ]
    assert all(option.description == "Shared population" for option in selector.options)


@pytest.mark.parametrize(
    ("composition", "event", "expected"),
    [
        (
            SafariComposition.SOLITARY,
            SafariThematicEvent.NONE,
            "Special Encounter: Solitary Pokémon",
        ),
        (
            SafariComposition.DUEL,
            SafariThematicEvent.NONE,
            "Special Encounter: Duel",
        ),
        (
            SafariComposition.HERD,
            SafariThematicEvent.NONE,
            "Special Encounter: Herd",
        ),
        (
            SafariComposition.NORMAL,
            SafariThematicEvent.FISHING,
            "Special Encounter: Fishing",
        ),
        (
            SafariComposition.NORMAL,
            SafariThematicEvent.THUNDERSTORM,
            "Special Encounter: Thunderstorm",
        ),
        (
            SafariComposition.NORMAL,
            SafariThematicEvent.BLIZZARD,
            "Special Encounter: Blizzard",
        ),
        (
            SafariComposition.NORMAL,
            SafariThematicEvent.TOXIC_BLOOM,
            "Special Encounter: Toxic Bloom",
        ),
    ],
)
def test_encounter_view_labels_special_encounters(
    composition,
    event,
    expected,
) -> None:
    session = make_session()
    encounter = make_encounter(
        composition=composition,
        event=event,
    )
    session.publish_encounter(encounter)
    view = SafariEncounterView(
        core=SimpleNamespace(),
        guild_id=session.guild_id,
        session=session,
    )

    content = view.build_content()
    if composition is SafariComposition.SOLITARY:
        assert "Special Encounter: Solitary Pokémon" not in content
    else:
        assert expected in content


def test_encounter_results_show_shared_captures_and_hide_unprocessed_unique_trainer():
    view, _ = _encounter_view()
    shared_opportunity = SimpleNamespace(species=create_species(id=25, name="Pikachu"))
    shared_outcome = SimpleNamespace(
        status=SimpleNamespace(name="CAPTURED"),
        final_opportunity=shared_opportunity,
    )
    shared_result = SimpleNamespace(
        slot_outcome=shared_outcome,
        creature=None,
        participant_results=(
            SimpleNamespace(
                participant_outcome=SimpleNamespace(
                    trainer_id=1,
                    attempts_executed=1,
                    balls_spent=1,
                ),
                creature=SimpleNamespace(species=shared_opportunity.species),
            ),
            SimpleNamespace(
                participant_outcome=SimpleNamespace(
                    trainer_id=2,
                    attempts_executed=2,
                    balls_spent=2,
                ),
                creature=SimpleNamespace(species=shared_opportunity.species),
            ),
        ),
    )
    unique_result = SimpleNamespace(
        slot_outcome=SimpleNamespace(
            status=SimpleNamespace(name="CAPTURED"),
            final_opportunity=shared_opportunity,
        ),
        participant_results=(
            SimpleNamespace(
                participant_outcome=SimpleNamespace(
                    trainer_id=3,
                    attempts_executed=1,
                    balls_spent=1,
                ),
                creature=SimpleNamespace(species=shared_opportunity.species),
            ),
            SimpleNamespace(
                participant_outcome=SimpleNamespace(
                    trainer_id=4,
                    attempts_executed=0,
                    balls_spent=0,
                ),
                creature=None,
            ),
        ),
        creature=None,
    )

    message = view._build_encounter_results_message(
        SimpleNamespace(slot_results=(shared_result, unique_result))
    )

    assert "<@1>" in message
    assert "<@2>" in message
    assert "<@3>" in message
    assert "<@4>" not in message
    assert "Pikachu - <@1> <@2> <@3>" in message
    assert message.count("Pikachu -") == 1
    assert "balls spent" not in message


def test_encounter_results_group_each_species_once() -> None:
    view, _ = _encounter_view()
    pikachu = create_species(id=25, name="Pikachu")
    eevee = create_species(id=133, name="Eevee")

    def result(species, trainer_id):
        outcome = SimpleNamespace(
            status=SimpleNamespace(name="CAPTURED"),
            final_opportunity=SimpleNamespace(species=species),
        )
        return SimpleNamespace(
            slot_outcome=outcome,
            creature=None,
            participant_results=(
                SimpleNamespace(
                    participant_outcome=SimpleNamespace(trainer_id=trainer_id),
                    creature=SimpleNamespace(species=species),
                ),
            ),
        )

    message = view._build_encounter_results_message(
        SimpleNamespace(
            slot_results=(result(pikachu, 1), result(pikachu, 2), result(eevee, 3))
        )
    )

    assert message.count("Pikachu -") == 1
    assert "Pikachu - <@1> <@2>" in message
    assert "Eevee - <@3>" in message


@pytest.mark.asyncio
async def test_choose_slot_opens_ball_count_view() -> None:
    view, session = _encounter_view()
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.choose_slot(interaction, session.current_encounter.slots[0].id)

    kwargs = interaction.response.send_message.await_args.kwargs
    assert kwargs["ephemeral"] is True
    assert kwargs["view"].__class__.__name__ == "SafariBallCountView"
    embed = kwargs["embed"]
    assert embed.title == "Choose Safari Balls"
    assert "Selected Pokémon:" in embed.description
    assert "Remaining Balls:" in embed.description


@pytest.mark.asyncio
async def test_ball_count_view_uses_player_facing_copy() -> None:
    view, session = _encounter_view()
    selection_view = SafariBallCountView(
        core=SimpleNamespace(),
        parent_view=view,
        trainer_id=1,
        slot_id=session.current_encounter.slots[0].id,
        slot_name="Starmie",
        remaining_balls=7,
        selectable_balls=3,
    )

    embed = selection_view.build_embed()

    assert embed.title == "Choose Safari Balls"
    assert "Shared population" in embed.description
    assert "Committed balls are spent only for executed attempts." in embed.description
    assert "Selected Pokémon: **Starmie**" in embed.description
    assert "Remaining Balls: 7" in embed.description
    assert [child.label for child in selection_view.children[:-1]] == [
        "1 Ball",
        "2 Balls",
        "3 Balls",
    ]
    assert selection_view.children[-1].label == "Decline"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ball_count", "available", "ball_label"),
    [(1, 4, "Safari Ball"), (2, 3, "Safari Balls")],
)
async def test_selection_flow_confirms_immediately(
    ball_count,
    available,
    ball_label,
) -> None:
    view, session = _encounter_view()
    view.core = SimpleNamespace(
        safari_capture_application=SimpleNamespace(
            select_capture=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    encounter=session.current_encounter,
                    participant=session.participants_by_trainer[1],
                    slot=session.current_encounter.slots[0],
                    balls_selected=ball_count,
                    balls_available=7,
                    selection=SimpleNamespace(
                        slot_id=session.current_encounter.slots[0].id,
                        ball_count=1,
                        is_confirmed=True,
                    ),
                    state=None,
                )
            ),
            confirm_capture_selection=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    encounter=session.current_encounter,
                    participant=session.participants_by_trainer[1],
                    selection=SimpleNamespace(
                        slot_id=session.current_encounter.slots[0].id,
                        ball_count=1,
                        is_confirmed=True,
                    ),
                    balls_spent=1,
                    balls_available=available,
                    state=None,
                )
            ),
            decline_capture=AsyncMock(return_value=SimpleNamespace()),
        ),
        safari_route_application=SimpleNamespace(),
        safari_finish_application=SimpleNamespace(),
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.select_balls(
        interaction,
        session.current_encounter.slots[0].id,
        ball_count,
    )

    assert interaction.response.send_message.await_count == 1
    assert f"Selected Pikachu with {ball_count} {ball_label}." in (
        interaction.response.send_message.await_args.kwargs["content"]
    )
    assert f"{ball_count} {ball_label} reserved for this encounter." in (
        interaction.response.send_message.await_args.kwargs["content"]
    )
    available_label = "Safari Ball" if available == 1 else "Safari Balls"
    assert f"{available} {available_label} available." in (
        interaction.response.send_message.await_args.kwargs["content"]
    )
    assert interaction.response.edit_message.await_count == 0


@pytest.mark.asyncio
async def test_selection_timeout_transitions_to_route_view(monkeypatch) -> None:
    monkeypatch.setattr(
        SafariRouteView,
        "start_route_timer",
        lambda self: None,
    )
    view, session = _encounter_view()
    route_vote = make_vote(session.current_segment.zone)
    old_message = AsyncMock()
    view.message = SimpleNamespace(
        channel=SimpleNamespace(
            id=321,
            send=AsyncMock(),
            fetch_message=AsyncMock(return_value=old_message),
        ),
        edit=AsyncMock(),
    )
    view.core = SimpleNamespace(
        safari_activity_tracker=SafariActivityTracker(),
        safari_capture_application=SimpleNamespace(
            close_capture_selection=AsyncMock(),
            resolve_capture=AsyncMock(
                return_value=ResolveSafariCaptureResult(
                    session=session,
                    encounter_resolution=SimpleNamespace(),
                    persisted_result=SimpleNamespace(),
                    slot_results=(),
                    rewards_by_trainer={},
                    balls_committed_by_trainer={},
                    next_session_status=SafariSessionStatus.ROUTE_DECISION,
                )
            ),
        ),
        safari_route_application=SimpleNamespace(
            open_route_vote=AsyncMock(
                return_value=SimpleNamespace(
                    session=session,
                    vote=route_vote,
                    options=route_vote.options,
                )
            ),
        ),
        safari_finish_application=SimpleNamespace(),
    )
    view.core.safari_activity_tracker.set_message(session.guild_id, 321, 99)

    await view._resolve_selection_timeout()

    old_message.delete.assert_awaited_once()
    assert view.message.channel.send.await_count == 1
    assert "Encounter Results" in view.message.channel.send.await_args.kwargs["content"]
    assert isinstance(
        view.message.channel.send.await_args.kwargs["view"],
        SafariRouteView,
    )
    assert view.message.channel.send.await_args.kwargs["file"].filename == "safari.png"


@pytest.mark.asyncio
async def test_selection_timeout_transitions_to_next_encounter(monkeypatch) -> None:
    start_selection_timer = Mock()
    monkeypatch.setattr(
        SafariEncounterView,
        "start_selection_timer",
        start_selection_timer,
    )
    view, session = _encounter_view()
    next_session = make_session()
    next_session.publish_encounter(make_encounter((27,)))
    old_message = AsyncMock()
    view.message = SimpleNamespace(
        channel=SimpleNamespace(
            id=321,
            send=AsyncMock(),
            fetch_message=AsyncMock(return_value=old_message),
        ),
        edit=AsyncMock(),
    )
    view.core = SimpleNamespace(
        safari_activity_tracker=SafariActivityTracker(),
        safari_capture_application=SimpleNamespace(
            close_capture_selection=AsyncMock(),
            resolve_capture=AsyncMock(
                return_value=ResolveSafariCaptureResult(
                    session=next_session,
                    encounter_resolution=SimpleNamespace(),
                    persisted_result=SimpleNamespace(),
                    slot_results=(),
                    rewards_by_trainer={},
                    balls_committed_by_trainer={},
                    next_session_status=SafariSessionStatus.ENCOUNTER,
                )
            ),
        ),
        safari_route_application=SimpleNamespace(
            open_route_vote=AsyncMock(),
        ),
        safari_finish_application=SimpleNamespace(),
    )
    view.core.safari_activity_tracker.set_message(session.guild_id, 321, 99)

    await view._resolve_selection_timeout()

    old_message.delete.assert_awaited_once()
    assert view.message.channel.send.await_count == 1
    assert "Encounter Results" in view.message.channel.send.await_args.kwargs["content"]
    assert isinstance(
        view.message.channel.send.await_args.kwargs["view"],
        SafariEncounterView,
    )
    assert view.message.channel.send.await_args.kwargs["file"].filename == (
        "safari-encounter.png"
    )
    assert (
        view.core.safari_activity_tracker.get_message(session.guild_id).message_id
        is None
    )
    start_selection_timer.assert_called_once()
    view.core.safari_route_application.open_route_vote.assert_not_awaited()


@pytest.mark.asyncio
async def test_selection_timeout_transitions_to_summary() -> None:
    view, session = _encounter_view(remaining_encounters=1)
    old_message = AsyncMock()
    view.message = SimpleNamespace(
        channel=SimpleNamespace(
            id=321,
            send=AsyncMock(),
            fetch_message=AsyncMock(return_value=old_message),
        ),
        edit=AsyncMock(),
    )
    view.core = SimpleNamespace(
        safari_activity_tracker=SafariActivityTracker(),
        safari_capture_application=SimpleNamespace(
            close_capture_selection=AsyncMock(),
            resolve_capture=AsyncMock(
                return_value=ResolveSafariCaptureResult(
                    session=session,
                    encounter_resolution=SimpleNamespace(),
                    persisted_result=SimpleNamespace(),
                    slot_results=(),
                    rewards_by_trainer={},
                    balls_committed_by_trainer={},
                    next_session_status=SafariSessionStatus.FINISHED,
                )
            ),
        ),
        safari_route_application=SimpleNamespace(),
        safari_finish_application=SimpleNamespace(
            finish=AsyncMock(
                return_value=SimpleNamespace(
                    summary=SimpleNamespace(
                        safari_map=session.safari_map,
                        weather=session.weather,
                        time_of_day=session.time_of_day,
                        finish_reason=SimpleNamespace(value="completed"),
                        totals=SimpleNamespace(encounters_completed=1),
                        ranking=(),
                    )
                )
            )
        ),
    )
    view.core.safari_activity_tracker.set_message(session.guild_id, 321, 99)

    await view._resolve_selection_timeout()

    old_message.delete.assert_awaited_once()
    assert view.message.channel.send.await_count == 1
    assert view.message.channel.send.await_args.kwargs["embeds"][0].title == (
        "Safari Complete"
    )
    assert (
        view.core.safari_activity_tracker.get_message(session.guild_id).message_id
        is None
    )


@pytest.mark.asyncio
async def test_encounter_timeout_edits_expired_note() -> None:
    view, _ = _encounter_view()
    view.message = AsyncMock()

    await view.on_timeout()

    assert (
        view.message.edit.await_args.kwargs["content"]
        == "This phase has already ended."
    )


@pytest.mark.asyncio
async def test_expired_encounter_rejects_old_callback() -> None:
    view, session = _encounter_view()
    view._phase_ended = True
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(
            is_done=lambda: False,
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
    )

    await view.choose_slot(interaction, session.current_encounter.slots[0].id)

    interaction.response.send_message.assert_awaited_once_with(
        "This phase has already ended.",
        ephemeral=True,
    )
