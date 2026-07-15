from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

from core.safari.domain import SafariMap, SafariZone
from core.species.species import Species

ROOT = Path(__file__).resolve().parents[1]
FONTS_ROOT = ROOT / "assets" / "fonts"
BACKGROUNDS_ROOT = ROOT / "assets" / "backgrounds"
REGULAR_ROOT = ROOT / "assets" / "regular"
SHINY_ROOT = ROOT / "assets" / "shiny"
PLACEHOLDER_SPECIES_ID = 25

logger = logging.getLogger(__name__)

BACKGROUND_BY_MAP: dict[SafariMap, str] = {
    SafariMap.FOREST: "grass.png",
    SafariMap.MOUNTAIN: "rock.png",
    SafariMap.COAST: "water.png",
    SafariMap.SWAMP: "poison.png",
    SafariMap.PLAINS: "normal.png",
}

BACKGROUND_BY_ZONE: dict[SafariZone, str] = {
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

BACKGROUND_BY_TYPE: dict[str, str] = {
    "bug": "bug.png",
    "dark": "dark.png",
    "dragon": "dragon.png",
    "electric": "electric.png",
    "fairy": "fairy.png",
    "fighting": "fighting.png",
    "fire": "fire.png",
    "flying": "flying.png",
    "ghost": "ghost.png",
    "grass": "grass.png",
    "ground": "ground.png",
    "ice": "ice.png",
    "normal": "normal.png",
    "poison": "poison.png",
    "psychic": "psychic.png",
    "rock": "rock.png",
    "steel": "steel.png",
    "water": "water.png",
}


class SafariAssets:
    @lru_cache(maxsize=8)
    def get_font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(FONTS_ROOT / "DejaVuSans-Bold.ttf", size)

    @lru_cache(maxsize=32)
    def get_background(self, safari_map: SafariMap) -> Image.Image:
        filename = BACKGROUND_BY_MAP.get(safari_map, "safari.png")
        return self.get_background_by_name(filename)

    @lru_cache(maxsize=32)
    def get_background_for_zone(self, zone: SafariZone) -> Image.Image:
        try:
            filename = BACKGROUND_BY_ZONE[zone]
        except KeyError as error:
            raise ValueError(
                f"Safari zone has no registered background: {zone}"
            ) from error

        path = BACKGROUNDS_ROOT / filename
        if not path.exists():
            raise FileNotFoundError(f"Safari zone background is missing: {path}")
        return Image.open(path).convert("RGBA")

    @lru_cache(maxsize=32)
    def get_background_by_name(self, name: str) -> Image.Image:
        filename = BACKGROUND_BY_TYPE.get(name, name)
        path = BACKGROUNDS_ROOT / filename
        if not path.exists():
            path = BACKGROUNDS_ROOT / "safari.png"
        return Image.open(path).convert("RGBA")

    @lru_cache(maxsize=2048)
    def get_sprite(self, species_id: int, shiny: bool) -> Image.Image:
        path = (SHINY_ROOT if shiny else REGULAR_ROOT) / f"{species_id}.png"
        if not path.exists():
            path = REGULAR_ROOT / f"{species_id}.png"
        return Image.open(path).convert("RGBA")

    def get_species_sprite(self, species: Species, shiny: bool) -> Image.Image:
        species_id = species.pokeapi_id
        path = (SHINY_ROOT if shiny else REGULAR_ROOT) / f"{species_id}.png"

        try:
            return self.get_sprite(species_id, shiny)
        except FileNotFoundError:
            logger.warning(
                "safari_sprite_missing species=%s asset_id=%s path=%s",
                species.name,
                species_id,
                path,
            )
            fallback_path = (SHINY_ROOT if shiny else REGULAR_ROOT) / (
                f"{PLACEHOLDER_SPECIES_ID}.png"
            )
            if not fallback_path.exists():
                raise
            return Image.open(fallback_path).convert("RGBA")
