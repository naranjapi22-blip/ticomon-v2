from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image, ImageFont

from application.safari import (
    SafariFinalSummary,
    SafariParticipantSummary,
    SafariRouteSegmentSummary,
    SafariRouteSummary,
    SafariTotalsSummary,
)
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariMap,
    SafariPhase,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)
from core.safari.domain import SafariFinishReason
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.participant import SafariParticipant
from rendering.safari.assets import BACKGROUND_BY_ZONE, BACKGROUNDS_ROOT, SafariAssets
from rendering.safari.layout import layout_slot_cards
from rendering.safari.renderer import SafariEncounterRenderer, SafariSummaryRenderer
from test.factories import create_species


def _session(slot_count: int = 3):
    participant = SafariParticipant(1, 3, 3)
    encounter = SafariEncounter(
        id=__import__("uuid").uuid4(),
        composition=SimpleNamespace(value="NORMAL"),
        slots=tuple(
            SafariEncounterSlot(
                uuid4(),
                OpportunityFactory.create(create_species(id=25 + index)),
            )
            for index in range(slot_count)
        ),
    )
    session = SimpleNamespace(
        current_encounter=encounter,
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
        phase=SafariPhase.START,
        completed_encounter_count=0,
        total_encounters=5,
        current_segment=SimpleNamespace(
            zone=SafariZone.FOREST_ENTRANCE,
            remaining_encounters=3,
        ),
        participants_by_trainer={1: participant},
    )
    return session


def _summary() -> SafariFinalSummary:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    captured = SimpleNamespace(
        collection_number=7,
        species=create_species(id=25),
        is_shiny=True,
        current_form=None,
    )
    ranking = (
        SafariParticipantSummary(
            rank=1,
            trainer_id=1,
            capture_count=1,
            shiny_capture_count=1,
            captured_creatures=(captured,),
            initial_balls=3,
            balls_used=2,
            balls_remaining=1,
            attempts_executed=2,
            slots_won=1,
            encounters_participated=1,
        ),
    )
    route = SafariRouteSummary(
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
        segments=(
            SafariRouteSegmentSummary(
                zone=SafariZone.FOREST_ENTRANCE,
                phase=SafariPhase.START,
                remaining_encounters=3,
                source_option_id=None,
            ),
        ),
    )
    encounters = (
        SimpleNamespace(
            slot_summaries=(
                SimpleNamespace(
                    slot_id=uuid4(),
                    species=create_species(id=25),
                    captured_creature=SimpleNamespace(
                        collection_number=7,
                        trainer_id=1,
                    ),
                ),
            )
        ),
    )
    return SafariFinalSummary(
        guild_id=10,
        session_id=uuid4(),
        level=4,
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
        started_at=now,
        finished_at=now,
        finish_reason=SafariFinishReason.COMPLETED,
        ranking=ranking,
        route=route,
        encounters=encounters,
        totals=SafariTotalsSummary(
            encounters_completed=1,
            pokemon_seen=3,
            slots_captured=1,
            slots_escaped=2,
            attempts_executed=2,
            balls_committed=2,
        ),
        extraordinary=SimpleNamespace(
            legendary_seen=False,
            mythical_seen=False,
            shiny_encounter_seen=True,
            regional_herd_seen=False,
        ),
    )


@pytest.mark.parametrize("slot_count", [1, 2, 3, 5])
def test_encounter_renderer_renders_supported_slot_counts(slot_count: int) -> None:
    image = SafariEncounterRenderer().render(_session(slot_count))

    assert image.size == (1020, 574)
    assert image.getbbox() is not None


def test_encounter_renderer_formats_long_species_names() -> None:
    assert (
        SafariEncounterRenderer.format_species_name("Dudunsparce-Two-Segment")
        == "Dudunsparce (Two-Segment)"
    )


def test_encounter_renderer_keeps_slot_background_transparent() -> None:
    class _FakeAssets:
        @staticmethod
        def get_background(_safari_map):
            return Image.new("RGBA", (1020, 574), (120, 160, 200, 255))

        @staticmethod
        def get_sprite(_species_id, _shiny):
            return Image.new("RGBA", (48, 48), (255, 255, 255, 255))

        @staticmethod
        def get_font(_size):
            return ImageFont.load_default()

    session = _session(1)
    image = SafariEncounterRenderer(assets=_FakeAssets()).render(session)
    placement = layout_slot_cards(1)[0]

    background_pixel = image.getpixel((10, 10))
    slot_pixel = image.getpixel((placement.x + 10, placement.y + 100))

    assert slot_pixel == background_pixel


def test_encounter_renderer_places_sprites_lower() -> None:
    class _FakeAssets:
        @staticmethod
        def get_background(_safari_map):
            return Image.new("RGBA", (1020, 574), (120, 160, 200, 255))

        @staticmethod
        def get_sprite(_species_id, _shiny):
            return Image.new("RGBA", (48, 48), (255, 255, 255, 255))

        @staticmethod
        def get_font(_size):
            return ImageFont.load_default()

    session = _session(1)
    image = SafariEncounterRenderer(assets=_FakeAssets()).render(session)
    placement = layout_slot_cards(1)[0]
    background_pixel = image.getpixel((10, 10))

    first_sprite_row = None
    for y in range(placement.y, placement.y + placement.height):
        for x in range(placement.x, placement.x + placement.width):
            if image.getpixel((x, y)) != background_pixel:
                first_sprite_row = y
                break
        if first_sprite_row is not None:
            break

    assert first_sprite_row is not None
    assert first_sprite_row >= placement.y + 10


def test_encounter_renderer_uses_zone_context_for_background() -> None:
    class _FakeAssets:
        def __init__(self) -> None:
            self.requested_backgrounds: list[str] = []

        @staticmethod
        def get_background(_safari_map):
            return Image.new("RGBA", (1020, 574), (120, 160, 200, 255))

        def get_background_by_name(self, name: str):
            self.requested_backgrounds.append(name)
            return Image.new("RGBA", (1020, 574), (120, 160, 200, 255))

        @staticmethod
        def get_sprite(_species_id, _shiny):
            return Image.new("RGBA", (48, 48), (255, 255, 255, 255))

        @staticmethod
        def get_font(_size):
            return ImageFont.load_default()

    assets = _FakeAssets()
    session = _session(1)
    session.safari_map = SafariMap.COAST
    session.current_segment = SimpleNamespace(
        zone=SafariZone.TIDAL_POOLS,
        remaining_encounters=3,
    )

    SafariEncounterRenderer(assets=assets).render(session)

    assert assets.requested_backgrounds[0] == "coast_tidal_pools.png"


def test_zone_background_catalog_covers_all_zones_and_files() -> None:
    assert BACKGROUND_BY_ZONE == {
        SafariZone.FOREST_ENTRANCE: "forest_entrance.png",
        SafariZone.DEEP_FOREST: "forest_deep_forest.png",
        SafariZone.RIVERBANK: "forest_riverbank.png",
        SafariZone.CLEARING: "forest_clearing.png",
        SafariZone.ANCIENT_GROVE: "forest_ancient_grove.png",
        SafariZone.MARSH_EDGE: "forest_marsh_edge.png",
        SafariZone.HILLSIDE_PATH: "forest_hillside_path.png",
        SafariZone.MOUNTAIN_FOOTHILL: "mountain_foothill.png",
        SafariZone.ROCKY_SLOPE: "mountain_rocky_slope.png",
        SafariZone.VALLEY: "mountain_valley.png",
        SafariZone.CAVE_ENTRANCE: "mountain_cave_entrance.png",
        SafariZone.DEEP_CAVE: "mountain_deep_cave.png",
        SafariZone.HIGH_RIDGE: "mountain_high_ridge.png",
        SafariZone.FROZEN_PASS: "mountain_frozen_pass.png",
        SafariZone.UNDERGROUND_LAKE: "mountain_underground_lake.png",
        SafariZone.SUMMIT: "mountain_summit.png",
        SafariZone.COAST_SHORE: "coast_shore.png",
        SafariZone.ROCKY_BEACH: "coast_rocky_beach.png",
        SafariZone.TIDAL_POOLS: "coast_tidal_pools.png",
        SafariZone.COASTAL_PATH: "coast_coastal_path.png",
        SafariZone.SEA_CAVE: "coast_sea_cave.png",
        SafariZone.CLIFFSIDE: "coast_cliffside.png",
        SafariZone.LAGOON: "coast_lagoon.png",
        SafariZone.MANGROVE_EDGE: "coast_mangrove_edge.png",
        SafariZone.DUNES: "coast_dunes.png",
        SafariZone.SWAMP_EDGE: "swamp_edge.png",
        SafariZone.MUDDY_TRAIL: "swamp_muddy_trail.png",
        SafariZone.SHALLOW_WATER: "swamp_shallow_water.png",
        SafariZone.DENSE_REEDS: "swamp_dense_reeds.png",
        SafariZone.DEAD_FOREST: "swamp_dead_forest.png",
        SafariZone.DEEP_MARSH: "swamp_deep_marsh.png",
        SafariZone.MISTY_CLEARING: "swamp_misty_clearing.png",
        SafariZone.NESTING_GROUND: "swamp_nesting_ground.png",
        SafariZone.OPEN_FIELD: "plains_open_field.png",
        SafariZone.PLAINS_TRAIL: "plains_trail.png",
        SafariZone.TALL_GRASS: "plains_tall_grass.png",
        SafariZone.FLOWER_MEADOW: "plains_flower_meadow.png",
        SafariZone.LOW_HILLS: "plains_low_hills.png",
        SafariZone.WINDY_FIELD: "plains_windy_field.png",
        SafariZone.RIVER_CROSSING: "plains_river_crossing.png",
        SafariZone.HERDING_GROUNDS: "plains_herding_grounds.png",
        SafariZone.ROCKY_OUTCROP: "plains_rocky_outcrop.png",
    }
    assert set(BACKGROUND_BY_ZONE) == set(SAFARI_ZONE_DEFINITION_BY_ZONE)
    assert len(BACKGROUND_BY_ZONE) == 42
    assert len(set(BACKGROUND_BY_ZONE.values())) == 42
    assert "safari.png" not in set(BACKGROUND_BY_ZONE.values())
    assert all(
        (BACKGROUNDS_ROOT / filename).is_file()
        for filename in set(BACKGROUND_BY_ZONE.values())
    )
    assert {path.name for path in BACKGROUNDS_ROOT.glob("*_*.png")} == set(
        BACKGROUND_BY_ZONE.values()
    )


def test_registered_zone_with_missing_file_is_reported(
    tmp_path,
    monkeypatch,
) -> None:
    import rendering.safari.assets as assets_module

    monkeypatch.setattr(assets_module, "BACKGROUNDS_ROOT", tmp_path)

    with pytest.raises(FileNotFoundError, match="forest_entrance.png"):
        SafariAssets().get_background_for_zone(SafariZone.FOREST_ENTRANCE)


def test_registered_zone_loads_existing_file(tmp_path, monkeypatch) -> None:
    import rendering.safari.assets as assets_module

    image_path = tmp_path / "forest_entrance.png"
    Image.new("RGBA", (400, 225), (20, 40, 60, 255)).save(image_path)
    monkeypatch.setattr(assets_module, "BACKGROUNDS_ROOT", tmp_path)

    image = SafariAssets().get_background_for_zone(SafariZone.FOREST_ENTRANCE)

    assert image.size == (400, 225)


@pytest.mark.parametrize(
    "zone",
    [
        SafariZone.RIVERBANK,
        SafariZone.ANCIENT_GROVE,
        SafariZone.MOUNTAIN_FOOTHILL,
        SafariZone.CAVE_ENTRANCE,
        SafariZone.SUMMIT,
        SafariZone.SEA_CAVE,
        SafariZone.DUNES,
        SafariZone.DENSE_REEDS,
        SafariZone.MISTY_CLEARING,
        SafariZone.FLOWER_MEADOW,
    ],
)
def test_second_group_registered_zones_report_missing_files(
    zone,
    tmp_path,
    monkeypatch,
) -> None:
    import rendering.safari.assets as assets_module

    monkeypatch.setattr(assets_module, "BACKGROUNDS_ROOT", tmp_path)

    with pytest.raises(FileNotFoundError):
        SafariAssets().get_background_for_zone(zone)


def test_encounter_renderer_uses_pokeapi_id_not_internal_id() -> None:
    class _FakeAssets:
        def __init__(self) -> None:
            self.requested_sprite_ids: list[int] = []

        @staticmethod
        def get_background(_safari_map):
            return Image.new("RGBA", (1020, 574), (120, 160, 200, 255))

        def get_sprite(self, species_id, _shiny):
            self.requested_sprite_ids.append(species_id)
            return Image.new("RGBA", (48, 48), (255, 255, 255, 255))

        @staticmethod
        def get_font(_size):
            return ImageFont.load_default()

    assets = _FakeAssets()
    species = SimpleNamespace(id=5132, pokeapi_id=132, name="Ditto")
    session = SimpleNamespace(
        current_encounter=SimpleNamespace(
            slots=(
                SimpleNamespace(
                    id=uuid4(),
                    opportunity=SimpleNamespace(
                        species=species,
                        is_shiny=False,
                    ),
                ),
            )
        ),
        safari_map=SafariMap.COAST,
        current_segment=SimpleNamespace(zone=None),
    )

    SafariEncounterRenderer(assets=assets).render(session)

    assert assets.requested_sprite_ids == [132]


def test_safari_assets_falls_back_to_placeholder_sprite(caplog) -> None:
    species = SimpleNamespace(id=5132, pokeapi_id=999999, name="Missingno")

    with caplog.at_level("WARNING"):
        sprite = SafariAssets().get_species_sprite(species, False)

    assert sprite.size == SafariAssets().get_sprite(25, False).size
    assert "safari_sprite_missing" in caplog.text
    assert "asset_id=999999" in caplog.text


def test_encounter_renderer_does_not_draw_slot_policy_badges() -> None:
    class _FakeAssets:
        @staticmethod
        def get_background(_safari_map):
            return Image.new("RGBA", (1020, 574), (120, 160, 200, 255))

        @staticmethod
        def get_sprite(_species_id, _shiny):
            return Image.new("RGBA", (48, 48), (255, 255, 255, 0))

        @staticmethod
        def get_font(_size):
            return ImageFont.load_default()

    session = _session(1)
    image = SafariEncounterRenderer(assets=_FakeAssets()).render(session)
    placement = layout_slot_cards(1)[0]

    badge_pixel = image.getpixel((placement.x + 24, placement.y + 24))
    background_pixel = image.getpixel((10, 10))

    assert badge_pixel == background_pixel


def test_encounter_renderer_keeps_long_names_readable() -> None:
    assert (
        SafariEncounterRenderer.format_species_name("Dudunsparce-Three-Segment")
        == "Dudunsparce (Three-Segment)"
    )


def test_summary_renderer_renders_final_banner() -> None:
    image = SafariSummaryRenderer().render(_summary())

    assert image.size == (1020, 574)
    assert image.getbbox() is not None
