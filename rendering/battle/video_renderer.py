from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence
from poke_env.battle.move import Move

from application.battle.battle_display_service import BattleDisplayService
from core.battle.engine.battle_result import BattleResult
from core.battle.engine.battle_step import BattleStepType
from rendering.battle.assets import HEIGHT, WIDTH, BattleAssets
from rendering.battle.frame_state import BattleFrameState
from rendering.battle.gif_assets import GifSequence, load_gif_sequence
from rendering.battle.sprite_urls import (
    battle_initiator_sprite_url,
    battle_opponent_sprite_url,
)

logger = logging.getLogger(__name__)

DEFAULT_SPECIAL_ATTACK_COLOR = (95, 205, 255)
SPECIAL_ATTACK_COLORS = {
    "normal": (220, 220, 220),
    "fire": (255, 90, 40),
    "water": (60, 150, 255),
    "electric": (255, 220, 50),
    "grass": (80, 200, 90),
    "ice": (130, 220, 255),
    "fighting": (200, 70, 60),
    "poison": (180, 80, 210),
    "ground": (190, 145, 75),
    "flying": (150, 180, 255),
    "psychic": (255, 90, 170),
    "bug": (160, 190, 50),
    "rock": (170, 145, 80),
    "ghost": (120, 90, 190),
    "dragon": (100, 80, 255),
    "dark": (90, 75, 75),
    "steel": (170, 180, 195),
    "fairy": (255, 150, 210),
}


class _AnimatedSprite:
    def __init__(self, sequence: GifSequence) -> None:
        self.frames = sequence.frames
        self.durations_ms = sequence.durations_ms
        self.total_duration_ms = sum(self.durations_ms)

    def frame_at(self, elapsed_seconds: float) -> Image.Image:
        elapsed_ms = int(elapsed_seconds * 1000) % self.total_duration_ms
        accumulated = 0
        for frame, duration in zip(self.frames, self.durations_ms, strict=True):
            accumulated += duration
            if elapsed_ms < accumulated:
                return frame.copy()
        return self.frames[-1].copy()


def _move_id_from_message(message: str) -> str | None:
    match = re.search(r" uses (.+)!", message)
    if match is None:
        return None
    return re.sub(r"[^a-z0-9]", "", match.group(1).lower())


def _visual_move_message(message: str) -> str:
    match = re.match(r"^.+?'s (?P<pokemon>.+?) uses (?P<move>.+)!$", message)
    if match is None:
        return message
    return f"{match.group('pokemon')} uses {match.group('move')}!"


def _animation_from_message(message: str) -> str:
    move_id = _move_id_from_message(message)
    if move_id is None:
        logger.warning("Could not resolve move from battle step: %s", message)
        return "special_attack"

    try:
        move = Move(move_id, gen=9)
    except Exception:
        logger.warning("Could not resolve move category for %s", move_id)
        return "special_attack"

    if move.category.name.lower() == "physical":
        return "physical_attack"
    return "special_attack"


def _special_attack_color(message: str) -> tuple[int, int, int]:
    move_id = _move_id_from_message(message)
    if move_id is None:
        return DEFAULT_SPECIAL_ATTACK_COLOR
    try:
        move = Move(move_id, gen=9)
        move_type = getattr(getattr(move, "type", None), "name", "").lower()
    except Exception:
        return DEFAULT_SPECIAL_ATTACK_COLOR
    return SPECIAL_ATTACK_COLORS.get(move_type, DEFAULT_SPECIAL_ATTACK_COLOR)


def _animation_frames(
    result: BattleResult,
    fighter_metadata: dict[str, tuple[tuple[int, bool], ...]],
    side_a_name: str,
    side_b_name: str,
) -> list[
    tuple[
        BattleStepType,
        BattleFrameState,
        str | None,
        tuple[int, int, int] | None,
    ]
]:
    display = BattleDisplayService()
    frames: list[
        tuple[
            BattleStepType,
            BattleFrameState,
            str | None,
            tuple[int, int, int] | None,
        ]
    ] = []
    pending_move: str | None = None
    pending_animation: str | None = None
    pending_color: tuple[int, int, int] | None = None
    turn_number = 0

    for step in result.steps:
        if step.step_type is BattleStepType.MOVE:
            pending_move = step.message
            pending_animation = _animation_from_message(step.message)
            pending_color = (
                _special_attack_color(step.message)
                if pending_animation == "special_attack"
                else None
            )
            continue
        if step.step_type is BattleStepType.DAMAGE:
            continue

        side_a_state = step.state_snapshot.get(step.side_a_name, {})
        side_b_state = step.state_snapshot.get(step.side_b_name, {})
        side_a_index = side_a_state.get("active_index", 0)
        side_b_index = side_b_state.get("active_index", 0)
        side_a_meta = fighter_metadata.get(side_a_name, ((25, False),))
        side_b_meta = fighter_metadata.get(side_b_name, ((6, False),))
        side_a_sprite = side_a_meta[min(side_a_index, len(side_a_meta) - 1)]
        side_b_sprite = side_b_meta[min(side_b_index, len(side_b_meta) - 1)]

        if step.step_type is BattleStepType.ATTACK:
            turn_number += 1
            message = " ".join(
                part
                for part in (
                    _visual_move_message(pending_move) if pending_move else None,
                    step.message,
                )
                if part
            )
            frame = display.frame_from_step(
                step,
                side_a_pokeapi_id=side_a_sprite[0],
                side_b_pokeapi_id=side_b_sprite[0],
                side_a_shiny=side_a_sprite[1],
                side_b_shiny=side_b_sprite[1],
                turn_number=turn_number,
                side_a_display_name=side_a_name,
                side_b_display_name=side_b_name,
            )
            frames.append(
                (
                    BattleStepType.ATTACK,
                    replace(frame, attack_line=message),
                    pending_animation,
                    pending_color,
                )
            )
            pending_move = None
            pending_animation = None
            pending_color = None
            continue

        if step.step_type in {
            BattleStepType.START,
            BattleStepType.SWITCH,
            BattleStepType.VICTORY,
        }:
            frame = display.frame_from_step(
                step,
                side_a_pokeapi_id=side_a_sprite[0],
                side_b_pokeapi_id=side_b_sprite[0],
                side_a_shiny=side_a_sprite[1],
                side_b_shiny=side_b_sprite[1],
                turn_number=turn_number,
                side_a_display_name=side_a_name,
                side_b_display_name=side_b_name,
            )
            if step.step_type is BattleStepType.VICTORY:
                frame = replace(
                    frame,
                    attack_line=(
                        f"🏆 Battle Complete\n{result.winner_side_name} wins!"
                    ),
                )
            frames.append((step.step_type, frame, None, None))

    return frames


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _interpolate_frame(
    previous: BattleFrameState,
    current: BattleFrameState,
    amount: float,
) -> BattleFrameState:
    amount = _ease(amount)
    return replace(
        current,
        side_a_hp=round(
            previous.side_a_hp + (current.side_a_hp - previous.side_a_hp) * amount
        ),
        side_b_hp=round(
            previous.side_b_hp + (current.side_b_hp - previous.side_b_hp) * amount
        ),
    )


@lru_cache(maxsize=32)
def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return BattleAssets().get_font(size)


def _sprite(
    *,
    pokeapi_id: int,
    shiny: bool,
    side_a: bool,
    local_path: Path | None = None,
) -> _AnimatedSprite:
    assets = BattleAssets()
    if local_path is not None:
        with Image.open(local_path) as source:
            frames = tuple(
                frame.convert("RGBA") for frame in ImageSequence.Iterator(source)
            )
            duration = int(source.info.get("duration", 100))
        return _AnimatedSprite(GifSequence(frames, (max(20, duration),) * len(frames)))

    url = (
        battle_initiator_sprite_url(pokeapi_id, shiny=shiny)
        if side_a
        else battle_opponent_sprite_url(pokeapi_id, shiny=shiny)
    )
    try:
        return _AnimatedSprite(load_gif_sequence(url))
    except Exception:
        image = assets.get_sprite(pokeapi_id, shiny=shiny).convert("RGBA")
        return _AnimatedSprite(GifSequence((image,), (100,)))


def _paste_centered(
    image: Image.Image,
    sprite: Image.Image,
    *,
    center_x: int,
    bottom_y: int,
    max_width: int,
    max_height: int,
) -> None:
    sprite = sprite.copy()
    sprite.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    image.alpha_composite(
        sprite,
        (center_x - sprite.width // 2, bottom_y - sprite.height),
    )


def _draw_effect(
    image: Image.Image,
    *,
    previous: BattleFrameState,
    current: BattleFrameState,
    progress: float,
    animation: str,
    color: tuple[int, int, int],
) -> None:
    if animation != "special_attack":
        return
    draw = ImageDraw.Draw(image, "RGBA")
    pulse = 1.0 - abs(progress * 2.0 - 1.0)
    alpha = round(190 * pulse)
    if current.side_b_hp < previous.side_b_hp:
        start, end = (365, 410), (800, 225)
    elif current.side_a_hp < previous.side_a_hp:
        start, end = (730, 235), (310, 420)
    else:
        return

    effect_x = round(start[0] + (end[0] - start[0]) * progress)
    effect_y = round(start[1] + (end[1] - start[1]) * progress)
    trail_progress = max(0.0, progress - 0.18)
    trail_x = round(start[0] + (end[0] - start[0]) * trail_progress)
    trail_y = round(start[1] + (end[1] - start[1]) * trail_progress)
    radius = 22 + round(8 * pulse)
    light_color = tuple(min(255, channel + 45) for channel in color)
    dark_color = tuple(max(0, channel - 35) for channel in color)
    draw.line(
        (trail_x, trail_y, effect_x, effect_y),
        fill=(*color, min(alpha + 70, 255)),
        width=18,
    )
    draw.ellipse(
        (
            effect_x - radius,
            effect_y - radius,
            effect_x + radius,
            effect_y + radius,
        ),
        fill=(*light_color, min(alpha + 45, 255)),
        outline=(*light_color, 255),
        width=3,
    )
    if progress >= 0.78:
        impact_progress = (progress - 0.78) / 0.22
        impact_alpha = round(220 * (1.0 - impact_progress))
        impact_radius = 28 + round(24 * impact_progress)
        draw.ellipse(
            (
                end[0] - impact_radius,
                end[1] - impact_radius,
                end[0] + impact_radius,
                end[1] + impact_radius,
            ),
            outline=(*light_color, impact_alpha),
            width=5,
        )
        for offset in (-1, 1):
            draw.line(
                (
                    end[0] + offset * 34,
                    end[1] - offset * 34,
                    end[0] + offset * 58,
                    end[1] - offset * 58,
                ),
                fill=(*dark_color, impact_alpha),
                width=4,
            )


def _draw_frame(
    *,
    background: Image.Image,
    frame: BattleFrameState,
    previous: BattleFrameState,
    step_type: BattleStepType,
    progress: float,
    elapsed_seconds: float,
    sprites: dict[tuple[int, bool, bool], _AnimatedSprite],
    animation: str | None,
    special_attack_color: tuple[int, int, int] | None = None,
) -> Image.Image:
    image = background.copy().convert("RGBA")
    player_x, player_y = 270, 500
    opponent_x, opponent_y = 800, 345
    if step_type is BattleStepType.ATTACK and animation == "physical_attack":
        lunge = _ease(1.0 - abs(progress * 2.0 - 1.0))
        if current_side_b_changed := frame.side_b_hp < previous.side_b_hp:
            player_x += round(90 * lunge)
            player_y -= round(25 * lunge)
        if current_side_a_changed := frame.side_a_hp < previous.side_a_hp:
            opponent_x -= round(75 * lunge)
            opponent_y += round(15 * lunge)
        if 0.35 <= progress <= 0.75:
            shake = 8 if int(progress * 30) % 2 == 0 else -8
            if current_side_b_changed:
                opponent_x += shake
            if current_side_a_changed:
                player_x += shake
    if (
        step_type is BattleStepType.ATTACK
        and animation == "special_attack"
        and progress >= 0.78
    ):
        reaction = 5 if int(progress * 30) % 2 == 0 else -5
        if frame.side_b_hp < previous.side_b_hp:
            opponent_x += reaction
        if frame.side_a_hp < previous.side_a_hp:
            player_x += reaction

    player_sprite = sprites[(frame.side_a_pokeapi_id, frame.side_a_shiny, True)]
    opponent_sprite = sprites[(frame.side_b_pokeapi_id, frame.side_b_shiny, False)]
    _paste_centered(
        image,
        player_sprite.frame_at(elapsed_seconds),
        center_x=player_x,
        bottom_y=player_y,
        max_width=305,
        max_height=280,
    )
    _paste_centered(
        image,
        opponent_sprite.frame_at(elapsed_seconds),
        center_x=opponent_x,
        bottom_y=opponent_y,
        max_width=280,
        max_height=250,
    )

    draw = ImageDraw.Draw(image, "RGBA")
    for x, y, right, trainer, pokemon, hp, hp_max in (
        (
            36,
            35,
            False,
            frame.side_b_name,
            frame.side_b_active_name,
            frame.side_b_hp,
            frame.side_b_hp_max,
        ),
        (
            WIDTH - 36,
            HEIGHT - 155,
            True,
            frame.side_a_name,
            frame.side_a_active_name,
            frame.side_a_hp,
            frame.side_a_hp_max,
        ),
    ):
        anchor = "ra" if right else "la"
        draw.text(
            (x, y),
            trainer,
            font=_font(28),
            anchor=anchor,
            fill="white",
            stroke_width=3,
            stroke_fill="black",
        )
        draw.text(
            (x, y + 34),
            pokemon,
            font=_font(23),
            anchor=anchor,
            fill="white",
            stroke_width=3,
            stroke_fill="black",
        )
        bar_x = x - 250 if right else x
        bar_y = y + 63
        fraction = 0 if hp_max <= 0 else max(0.0, min(1.0, hp / hp_max))
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + 250, bar_y + 17),
            radius=5,
            fill=(55, 55, 55, 225),
            outline=(20, 20, 20, 255),
            width=2,
        )
        if fraction > 0:
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + round(250 * fraction), bar_y + 17),
                radius=5,
                fill=(255, 204, 0, 255),
            )
        hp_x = bar_x - 10 if right else bar_x + 260
        draw.text(
            (hp_x, bar_y + 8),
            f"{hp}/{hp_max}",
            font=_font(19),
            anchor="ra" if right else "la",
            fill="white",
            stroke_width=3,
            stroke_fill="black",
        )

    if step_type is BattleStepType.ATTACK:
        _draw_effect(
            image,
            previous=previous,
            current=frame,
            progress=progress,
            animation=animation or "special_attack",
            color=special_attack_color or DEFAULT_SPECIAL_ATTACK_COLOR,
        )
    if step_type is BattleStepType.VICTORY:
        draw.multiline_text(
            (WIDTH // 2, HEIGHT // 2),
            frame.attack_line,
            font=_font(30),
            anchor="mm",
            align="center",
            fill="white",
            stroke_width=3,
            stroke_fill="black",
        )
        return image.convert("RGB")

    draw.rounded_rectangle(
        (28, HEIGHT - 80, WIDTH - 28, HEIGHT - 20),
        radius=14,
        fill=(0, 0, 0, 190),
        outline="white",
        width=2,
    )
    draw.multiline_text(
        (WIDTH // 2, HEIGHT - 67),
        frame.attack_line,
        font=_font(24),
        anchor="ma",
        align="center",
        fill="white",
        stroke_width=2,
        stroke_fill="black",
    )
    return image.convert("RGB")


def _step_duration(step_type: BattleStepType) -> float:
    return {
        BattleStepType.START: 1.0,
        BattleStepType.ATTACK: 1.00,
        BattleStepType.SWITCH: 0.80,
        BattleStepType.VICTORY: 2.40,
    }[step_type]


def render_battle_video(
    result: BattleResult,
    fighter_metadata: dict[str, tuple[tuple[int, bool], ...]],
    side_a_name: str,
    side_b_name: str,
    background: Image.Image,
    output_path: Path,
    *,
    fps: int = 20,
    crf: int = 27,
    sprite_paths: tuple[Path, Path] | None = None,
) -> tuple[float, int, int, int, str]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg was not found in PATH.")

    display_frames = _animation_frames(
        result,
        fighter_metadata,
        side_a_name,
        side_b_name,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sprites: dict[tuple[int, bool, bool], _AnimatedSprite] = {}
    for side_name, side_a in ((side_a_name, True), (side_b_name, False)):
        for pokeapi_id, shiny in fighter_metadata.get(
            side_name,
            ((25, False),) if side_a else ((6, False),),
        ):
            sprites[(pokeapi_id, shiny, side_a)] = _sprite(
                pokeapi_id=pokeapi_id,
                shiny=shiny,
                side_a=side_a,
                local_path=(sprite_paths[0 if side_a else 1] if sprite_paths else None),
            )
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None
    started = time.perf_counter()
    total_frames = 0
    previous_frame = display_frames[0][1]
    try:
        for step_type, current_frame, animation, special_attack_color in display_frames:
            count = max(1, round(_step_duration(step_type) * fps))
            for frame_index in range(count):
                progress = frame_index / max(count - 1, 1)
                shown = (
                    _interpolate_frame(previous_frame, current_frame, progress)
                    if step_type is BattleStepType.ATTACK
                    else current_frame
                )
                image = _draw_frame(
                    background=background,
                    frame=shown,
                    previous=previous_frame,
                    step_type=step_type,
                    progress=progress,
                    elapsed_seconds=total_frames / fps,
                    sprites=sprites,
                    animation=animation,
                    special_attack_color=special_attack_color,
                )
                process.stdin.write(image.tobytes())
                total_frames += 1
            previous_frame = current_frame
    finally:
        process.stdin.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace")
    if process.wait() != 0:
        raise RuntimeError(f"FFmpeg failed: {stderr}")
    return (
        time.perf_counter() - started,
        total_frames,
        len(result.steps),
        len(display_frames),
        result.winner_side_name,
    )
