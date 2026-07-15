from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

from core.safari.domain import SafariMap, SafariZone
from core.species.species import Species

ROOT = Path(__file__).resolve().parents[1]
FONTS_ROOT = ROOT / "assets" / "fonts"
FONDOS_ROOT = ROOT / "assets" / "fondos"
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
    SafariZone.ROCKY_SLOPE: "mountain_rocky_slope.png",
    SafariZone.DEEP_CAVE: "mountain_deep_cave.png",
    SafariZone.COAST_SHORE: "coast_shore.png",
    SafariZone.TIDAL_POOLS: "coast_tidal_pools.png",
    SafariZone.SWAMP_EDGE: "swamp_edge.png",
    SafariZone.DEAD_FOREST: "swamp_dead_forest.png",
    SafariZone.OPEN_FIELD: "plains_open_field.png",
    SafariZone.TALL_GRASS: "plains_tall_grass.png",
    SafariZone.RIVERBANK: "forest_riverbank.png",
    SafariZone.ANCIENT_GROVE: "forest_ancient_grove.png",
    SafariZone.MOUNTAIN_FOOTHILL: "mountain_foothill.png",
    SafariZone.CAVE_ENTRANCE: "mountain_cave_entrance.png",
    SafariZone.SUMMIT: "mountain_summit.png",
    SafariZone.SEA_CAVE: "coast_sea_cave.png",
    SafariZone.DUNES: "coast_dunes.png",
    SafariZone.DENSE_REEDS: "swamp_dense_reeds.png",
    SafariZone.MISTY_CLEARING: "swamp_misty_clearing.png",
    SafariZone.FLOWER_MEADOW: "plains_flower_meadow.png",
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
    def get_background_for_zone(self, zone: SafariZone | None) -> Image.Image:
        filename = BACKGROUND_BY_ZONE.get(zone, "safari.png")
        return self.get_background_by_name(filename)

    @lru_cache(maxsize=32)
    def get_background_by_name(self, name: str) -> Image.Image:
        filename = BACKGROUND_BY_TYPE.get(name, name)
        path = FONDOS_ROOT / filename
        if not path.exists():
            path = FONDOS_ROOT / "safari.png"
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
