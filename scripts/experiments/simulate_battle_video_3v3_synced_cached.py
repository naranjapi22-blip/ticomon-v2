from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence
from poke_env.battle.move import Move

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from application.battle.battle_display_service import BattleDisplayService
from core.battle.engine.battle_fighter import BattleFighter
from core.battle.engine.battle_simulator import BattleSimulator
from core.battle.engine.battle_step import BattleStepType
from core.battle.ports.damage_calculator import DamageCalculator, DamageResult
from rendering.battle.assets import HEIGHT, WIDTH, BattleAssets
from rendering.battle.frame_state import BattleFrameState


class DemoDamageCalculator(DamageCalculator):
    """Deterministic damage used only by this isolated experiment."""

    def calculate(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
        *,
        random_source,
    ) -> DamageResult:
        damage = 26 if attacker.display_name == "Pikachu" else 21
        return DamageResult(
            damage=damage,
            hit=True,
            critical=False,
            effectiveness_label="",
            message=f"{attacker.display_name} hits {defender.display_name}.",
        )


class DeterministicRandom:
    def randint(self, a: int, b: int) -> int:
        return a

    def random(self) -> float:
        return 0.5

    def sample(self, population: list, k: int) -> list:
        return list(population[:k])


class AnimatedGif:
    def __init__(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"GIF not found: {path}")

        self.frames: list[Image.Image] = []
        self.durations_ms: list[int] = []

        with Image.open(path) as source:
            default_duration = int(source.info.get("duration", 100))
            for frame in ImageSequence.Iterator(source):
                self.frames.append(frame.convert("RGBA"))
                self.durations_ms.append(
                    max(20, int(frame.info.get("duration", default_duration)))
                )

        if not self.frames:
            raise ValueError(f"GIF has no frames: {path}")

        self.total_duration_ms = sum(self.durations_ms)

    def frame_at(self, elapsed_seconds: float) -> Image.Image:
        elapsed_ms = int(elapsed_seconds * 1000) % self.total_duration_ms
        accumulated = 0

        for frame, duration in zip(self.frames, self.durations_ms, strict=True):
            accumulated += duration
            if elapsed_ms < accumulated:
                return frame.copy()

        return self.frames[-1].copy()


def build_fighter(
    *,
    creature_id: int,
    name: str,
    showdown_id: str,
    pokeapi_id: int,
    pokemon_type: str,
    hp: int,
    speed: int,
    move_id: str,
    move_name: str,
) -> BattleFighter:
    return BattleFighter(
        creature_id=creature_id,
        display_name=name,
        species_showdown_id=showdown_id,
        nature_showdown_id="hardy",
        types=(pokemon_type,),
        hp_max=hp,
        attack=70,
        special_attack=70,
        defense=65,
        special_defense=65,
        speed=speed,
        move_id=move_id,
        move_display_name=move_name,
        pokeapi_id=pokeapi_id,
        is_shiny=False,
    )


def animation_for_move(move_id: str) -> str:
    move = Move(move_id, gen=9)
    if move.category.name.lower() == "physical":
        return "physical_attack"
    return "special_attack"


def simulate_battle():
    pikachu_moves = (
        ("thunderbolt", "Thunderbolt"),
        ("quickattack", "Quick Attack"),
        ("thunderbolt", "Thunderbolt"),
    )
    charizard_moves = (
        ("flamethrower", "Flamethrower"),
        ("tackle", "Tackle"),
        ("flamethrower", "Flamethrower"),
    )
    pikachu_team = tuple(
        build_fighter(
            creature_id=index,
            name=f"Pikachu {index}",
            showdown_id="pikachu",
            pokeapi_id=25,
            pokemon_type="electric",
            hp=100,
            speed=110,
            move_id=move_id,
            move_name=move_name,
        )
        for index, (move_id, move_name) in enumerate(pikachu_moves, 1)
    )
    charizard_team = tuple(
        build_fighter(
            creature_id=100 + index,
            name=f"Charizard {index}",
            showdown_id="charizard",
            pokeapi_id=6,
            pokemon_type="fire",
            hp=100,
            speed=95,
            move_id=move_id,
            move_name=move_name,
        )
        for index, (move_id, move_name) in enumerate(charizard_moves, 1)
    )

    simulator = BattleSimulator(
        DemoDamageCalculator(),
        random_source=DeterministicRandom(),
    )
    result = simulator.run(
        pikachu_team,
        charizard_team,
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_trainer_id=1,
        side_b_trainer_id=2,
    )
    move_animations = {
        fighter.move_display_name: animation_for_move(fighter.move_id)
        for fighter in (*pikachu_team, *charizard_team)
    }
    return result, move_animations


def build_display_frames(
    result,
    move_animations: dict[str, str],
) -> list[tuple[BattleStepType, BattleFrameState, str | None]]:
    """
    Convert the Core's detailed events into coherent visual scenes.

    MOVE, DAMAGE and ATTACK belong to one action. The ATTACK snapshot contains
    the resulting HP, while the three messages together explain what happened.
    """
    display = BattleDisplayService()
    frames: list[tuple[BattleStepType, BattleFrameState, str | None]] = []

    pending_move_message: str | None = None
    pending_damage_message: str | None = None
    pending_animation: str | None = None
    visual_turn = 0

    for step in result.steps:
        if step.step_type == BattleStepType.MOVE:
            pending_move_message = step.message
            pending_damage_message = None
            pending_animation = next(
                (
                    animation
                    for move_name, animation in move_animations.items()
                    if f"uses {move_name}!" in step.message
                ),
                "special_attack",
            )
            continue

        if step.step_type == BattleStepType.DAMAGE:
            pending_damage_message = step.message
            continue

        if step.step_type == BattleStepType.ATTACK:
            visual_turn += 1
            message_parts = [
                part
                for part in (
                    pending_move_message,
                    pending_damage_message,
                    step.message,
                )
                if part
            ]
            frame = display.frame_from_step(
                step,
                side_a_pokeapi_id=25,
                side_b_pokeapi_id=6,
                side_a_shiny=False,
                side_b_shiny=False,
                turn_number=visual_turn,
                side_a_display_name="Alice",
                side_b_display_name="Bob",
            )
            frames.append(
                (
                    BattleStepType.ATTACK,
                    replace(frame, attack_line=" ".join(message_parts)),
                    pending_animation,
                )
            )
            pending_move_message = None
            pending_damage_message = None
            pending_animation = None
            continue

        if step.step_type in {
            BattleStepType.START,
            BattleStepType.SWITCH,
            BattleStepType.VICTORY,
        }:
            frame = display.frame_from_step(
                step,
                side_a_pokeapi_id=25,
                side_b_pokeapi_id=6,
                side_a_shiny=False,
                side_b_shiny=False,
                turn_number=visual_turn,
                side_a_display_name="Alice",
                side_b_display_name="Bob",
            )
            frames.append((step.step_type, frame, None))

    return frames


def ease_in_out(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def interpolate_frame(
    previous: BattleFrameState,
    current: BattleFrameState,
    amount: float,
) -> BattleFrameState:
    amount = ease_in_out(amount)
    return replace(
        current,
        side_a_hp=round(
            previous.side_a_hp + (current.side_a_hp - previous.side_a_hp) * amount
        ),
        side_b_hp=round(
            previous.side_b_hp + (current.side_b_hp - previous.side_b_hp) * amount
        ),
    )


@lru_cache(maxsize=None)
def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def contain_sprite(
    sprite: Image.Image,
    *,
    max_width: int,
    max_height: int,
) -> Image.Image:
    sprite = sprite.copy()
    sprite.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return sprite


def paste_centered(
    canvas: Image.Image,
    sprite: Image.Image,
    *,
    center_x: int,
    bottom_y: int,
) -> None:
    x = center_x - sprite.width // 2
    y = bottom_y - sprite.height
    canvas.alpha_composite(sprite, (x, y))


def draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    *,
    anchor: str,
) -> None:
    draw.text(
        xy,
        text,
        font=font,
        anchor=anchor,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 255),
    )


def draw_hp_panel(
    image: Image.Image,
    *,
    x: int,
    y: int,
    align_right: bool,
    trainer_name: str,
    pokemon_name: str,
    hp: int,
    hp_max: int,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    trainer_font = load_font(28)
    pokemon_font = load_font(23)
    hp_font = load_font(19)

    width = 250
    bar_height = 17
    anchor = "ra" if align_right else "la"

    draw_outlined_text(
        draw,
        (x, y),
        trainer_name,
        trainer_font,
        anchor=anchor,
    )
    draw_outlined_text(
        draw,
        (x, y + 34),
        pokemon_name,
        pokemon_font,
        anchor=anchor,
    )

    bar_x = x - width if align_right else x
    bar_y = y + 63
    fraction = 0 if hp_max <= 0 else max(0.0, min(1.0, hp / hp_max))
    fill_width = round(width * fraction)

    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + width, bar_y + bar_height),
        radius=5,
        fill=(55, 55, 55, 225),
        outline=(20, 20, 20, 255),
        width=2,
    )
    if fill_width > 0:
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + fill_width, bar_y + bar_height),
            radius=5,
            fill=(255, 204, 0, 255),
        )

    hp_text = f"{hp}/{hp_max}"
    hp_x = bar_x - 10 if align_right else bar_x + width + 10
    hp_anchor = "ra" if align_right else "la"
    draw_outlined_text(
        draw,
        (hp_x, bar_y + bar_height // 2),
        hp_text,
        hp_font,
        anchor=hp_anchor,
    )


@lru_cache(maxsize=256)
def build_caption_overlay(message: str) -> Image.Image:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    font = load_font(24)

    left = 28
    top = HEIGHT - 80
    right = WIDTH - 28
    bottom = HEIGHT - 20

    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=14,
        fill=(0, 0, 0, 190),
        outline=(255, 255, 255, 220),
        width=2,
    )

    max_width = (right - left) - 32
    words = message.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        text_width = draw.textbbox((0, 0), candidate, font=font)[2]
        if text_width <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
        current = word

        if len(lines) == 1:
            break

    if current and len(lines) < 2:
        lines.append(current)

    shown_text = "\n".join(lines[:2])
    draw.multiline_text(
        (WIDTH // 2, top + 13),
        shown_text,
        font=font,
        anchor="ma",
        align="center",
        fill=(255, 255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
        spacing=2,
    )
    return overlay


def draw_caption(image: Image.Image, message: str) -> None:
    image.alpha_composite(build_caption_overlay(message))


def draw_effect(
    image: Image.Image,
    *,
    previous: BattleFrameState,
    current: BattleFrameState,
    progress: float,
    animation: str,
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
    radius = 22 + round(10 * pulse)
    draw.line(
        (start[0], start[1], effect_x, effect_y),
        fill=(120, 220, 255, min(alpha + 50, 255)),
        width=12,
    )
    draw.ellipse(
        (
            effect_x - radius,
            effect_y - radius,
            effect_x + radius,
            effect_y + radius,
        ),
        fill=(220, 250, 255, alpha),
        outline=(255, 255, 255, min(alpha + 50, 255)),
        width=4,
    )


def draw_pokemon(
    image: Image.Image,
    *,
    player_gif: AnimatedGif,
    opponent_gif: AnimatedGif,
    elapsed_seconds: float,
    previous: BattleFrameState,
    current: BattleFrameState,
    progress: float,
    step_type: BattleStepType,
    animation: str | None,
) -> None:
    player = contain_sprite(
        player_gif.frame_at(elapsed_seconds),
        max_width=305,
        max_height=280,
    )
    opponent = contain_sprite(
        opponent_gif.frame_at(elapsed_seconds),
        max_width=280,
        max_height=250,
    )

    player_x = 270
    player_y = 500
    opponent_x = 800
    opponent_y = 345

    if step_type == BattleStepType.ATTACK and animation == "physical_attack":
        side_a_attacking = current.side_b_hp < previous.side_b_hp
        side_b_attacking = current.side_a_hp < previous.side_a_hp
        lunge = ease_in_out(1.0 - abs(progress * 2.0 - 1.0))

        if side_a_attacking:
            player_x += round(90 * lunge)
            player_y -= round(25 * lunge)
        if side_b_attacking:
            opponent_x -= round(75 * lunge)
            opponent_y += round(15 * lunge)

        if 0.35 <= progress <= 0.75:
            shake = 8 if int(progress * 30) % 2 == 0 else -8
            if current.side_b_hp < previous.side_b_hp:
                opponent_x += shake
            if current.side_a_hp < previous.side_a_hp:
                player_x += shake

    paste_centered(
        image,
        player,
        center_x=player_x,
        bottom_y=player_y,
    )
    paste_centered(
        image,
        opponent,
        center_x=opponent_x,
        bottom_y=opponent_y,
    )


def step_duration(step_type: BattleStepType) -> float:
    return {
        BattleStepType.START: 1.0,
        BattleStepType.ATTACK: 0.60,
        BattleStepType.SWITCH: 0.80,
        BattleStepType.VICTORY: 1.40,
    }[step_type]


def render_scene(
    *,
    background: Image.Image,
    frame: BattleFrameState,
    previous: BattleFrameState,
    step_type: BattleStepType,
    progress: float,
    elapsed_seconds: float,
    player_gif: AnimatedGif,
    opponent_gif: AnimatedGif,
    animation: str | None,
) -> Image.Image:
    image = background.copy().convert("RGBA")

    draw_pokemon(
        image,
        player_gif=player_gif,
        opponent_gif=opponent_gif,
        elapsed_seconds=elapsed_seconds,
        previous=previous,
        current=frame,
        progress=progress,
        step_type=step_type,
        animation=animation,
    )

    draw_hp_panel(
        image,
        x=36,
        y=35,
        align_right=False,
        trainer_name=frame.side_b_name,
        pokemon_name=frame.side_b_active_name,
        hp=frame.side_b_hp,
        hp_max=frame.side_b_hp_max,
    )
    draw_hp_panel(
        image,
        x=WIDTH - 36,
        y=HEIGHT - 155,
        align_right=True,
        trainer_name=frame.side_a_name,
        pokemon_name=frame.side_a_active_name,
        hp=frame.side_a_hp,
        hp_max=frame.side_a_hp_max,
    )

    if step_type == BattleStepType.ATTACK:
        draw_effect(
            image,
            previous=previous,
            current=frame,
            progress=progress,
            animation=animation or "special_attack",
        )

    draw_caption(image, frame.attack_line)
    return image.convert("RGB")


def encode_video(
    *,
    output_path: Path,
    player_path: Path,
    opponent_path: Path,
    fps: int,
    crf: int,
    battle_id: int,
) -> tuple[float, int, int, int, str]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg was not found in PATH.")

    result, move_animations = simulate_battle()
    display_frames = build_display_frames(result, move_animations)

    assets = BattleAssets()
    background = assets.get_background_for_battle(battle_id)
    player_gif = AnimatedGif(player_path)
    opponent_gif = AnimatedGif(opponent_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None

    started = time.perf_counter()
    total_frames = 0
    previous_frame = display_frames[0][1]

    try:
        for step_type, current_frame, animation in display_frames:
            duration = step_duration(step_type)
            count = max(1, round(duration * fps))

            for frame_index in range(count):
                progress = frame_index / max(count - 1, 1)

                if step_type == BattleStepType.ATTACK:
                    shown = interpolate_frame(
                        previous_frame,
                        current_frame,
                        progress,
                    )
                else:
                    shown = current_frame

                elapsed_seconds = total_frames / fps
                image = render_scene(
                    background=background,
                    frame=shown,
                    previous=previous_frame,
                    step_type=step_type,
                    progress=progress,
                    elapsed_seconds=elapsed_seconds,
                    player_gif=player_gif,
                    opponent_gif=opponent_gif,
                    animation=animation,
                )
                process.stdin.write(image.tobytes())
                total_frames += 1

            previous_frame = current_frame

    except BrokenPipeError as exc:
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg stopped unexpectedly:\n{stderr}") from exc
    finally:
        process.stdin.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace")
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"FFmpeg failed with exit code {return_code}:\n{stderr}")

    elapsed = time.perf_counter() - started
    return (
        elapsed,
        total_frames,
        len(result.steps),
        len(display_frames),
        result.winner_side_name,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Isolated experiment: simulate a grouped 3v3 TicoMon battle and "
            "render it with Showdown GIFs only."
        )
    )
    parser.add_argument("--player", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("complete_battle_3v3_synced_cached.mp4"),
    )
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--crf", type=int, default=27)
    parser.add_argument("--battle-id", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.fps <= 0:
        raise SystemExit("--fps must be greater than zero.")
    if not 0 <= args.crf <= 51:
        raise SystemExit("--crf must be between 0 and 51.")

    elapsed, frame_count, step_count, visual_scene_count, winner = encode_video(
        output_path=args.output,
        player_path=args.player,
        opponent_path=args.opponent,
        fps=args.fps,
        crf=args.crf,
        battle_id=args.battle_id,
    )

    output = args.output.resolve()
    size_mb = output.stat().st_size / (1024 * 1024)
    duration = frame_count / args.fps

    print(f"Created: {output}")
    print(f"Winner: {winner}")
    print(f"Battle steps: {step_count}")
    print(f"Visual scenes: {visual_scene_count}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Frames: {frame_count} at {args.fps} FPS")
    print(f"Render time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
