"""
============================================================

TicoMon Animation Engine
capture_animation.py

Version 1.0

Capture animation engine.

============================================================
"""

from __future__ import annotations

import math
import random
import time
from io import BytesIO
from pathlib import Path

from PIL import (
    Image,
    ImageDraw,
    ImageSequence,
)

BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

BACKGROUNDS_DIR = ASSETS_DIR / "fondos"

POKEBALLS_DIR = ASSETS_DIR / "pokeballs"

# ============================================================
# CONFIGURATION
# ============================================================

WIDTH = 400
HEIGHT = 225


CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

BALL_START_X = 20
BALL_START_Y = HEIGHT - 60

FPS = 24
FRAME_DURATION = 80

SPRITE_SIZE = 140
GROUND_Y = HEIGHT - 40
# ============================================================
# COLORS
# ============================================================

BACKGROUND_TOP = (35, 120, 45)
BACKGROUND_BOTTOM = (90, 180, 80)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

GOLD = (255, 220, 60)

RED = (230, 50, 50)

BLUE = (90, 170, 255)

GREEN = (90, 255, 120)

CYAN = (150, 240, 255)


# ============================================================
# UTILITIES
# ============================================================


def lerp(a, b, t):

    return a + (b - a) * t


def clamp(v, a, b):

    return max(a, min(v, b))


def ease_out(t):

    t = clamp(t, 0, 1)

    return 1 - (1 - t) ** 3


def ease_in_out(t):

    t = clamp(t, 0, 1)

    return -(math.cos(math.pi * t) - 1) / 2


# ============================================================
# SPRITES
# ============================================================


def load_sprite(path):

    path = Path(path)

    if not path.exists():

        raise FileNotFoundError(path)

    return Image.open(path).convert("RGBA")


def load_gif_frames(path, size=SPRITE_SIZE):

    if str(path).startswith("http"):

        from urllib.error import HTTPError
        from urllib.request import Request, urlopen

        try:

            req = Request(path, headers={"User-Agent": "Mozilla/5.0"})

            with urlopen(req) as response:
                data = response.read()

            gif = Image.open(BytesIO(data))

        except HTTPError as e:

            if e.code != 404:
                raise

            path = path.replace("/shiny/", "/regular/")

            req = Request(path, headers={"User-Agent": "Mozilla/5.0"})

            with urlopen(req) as response:
                data = response.read()

            gif = Image.open(BytesIO(data))

    else:

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(path)

        gif = Image.open(path)

    frames = []
    durations = []

    for frame in ImageSequence.Iterator(gif):

        img = frame.convert("RGBA")

        bbox = img.getbbox()

        if bbox:
            img = img.crop(bbox)

        frames.append(img)

        duration = frame.info.get("duration", 80)

        if not duration or duration <= 0:
            duration = 80

        durations.append(duration)

    return frames, durations


def load_pokeball(type_name):
    filename = type_name.lower().replace("é", "e").replace(" ", "_") + ".png"

    return Image.open(POKEBALLS_DIR / filename).convert("RGBA")


TRAINERS_DIR = ASSETS_DIR / "trainers"


def load_trainer(name: str):

    frames, _ = load_gif_frames(TRAINERS_DIR / f"{name}.gif")

    return frames


def white_sprite(sprite):

    alpha = sprite.getchannel("A")

    blanco = Image.new("RGBA", sprite.size, WHITE)

    blanco.putalpha(alpha)

    return blanco


def resize_sprite(sprite, size):

    scale = min(size / sprite.width, size / sprite.height)

    return sprite.resize(
        (int(sprite.width * scale), int(sprite.height * scale)), Image.LANCZOS
    )


# ============================================================
# BACKGROUND
# ============================================================


class Background:

    def __init__(self, type_name=None):

        if type_name:

            path = BACKGROUNDS_DIR / f"{type_name}.png"

            if path.exists():

                self.background = Image.open(path).convert("RGBA")

            else:

                path = random.choice(list(BACKGROUNDS_DIR.glob("*.png")))

                self.background = Image.open(path).convert("RGBA")

        else:

            path = random.choice(list(BACKGROUNDS_DIR.glob("*.png")))

            self.background = Image.open(path).convert("RGBA")

        self.background = self.background.resize((WIDTH, HEIGHT), Image.NEAREST)

    def render(self, frame):

        return self.background.copy()


BACKGROUND = Background()


# ============================================================
# CAMERA
# ============================================================


class Camera:

    def __init__(self):

        self.zoom = 1

        self.offset_x = 0

        self.offset_y = 0

    def update(self, frame):

        self.zoom = 1

        self.offset_x = 0
        self.offset_y = 0

        self.zoom += math.sin(frame * 0.18) * 0.02

        # Small impact zoom.

        if 8 <= frame <= 13:

            t = ease_out((frame - 8) / 5)

            self.zoom += t * 0.18

        elif frame > 13:

            t = ease_out(min(1, (frame - 13) / 5))

            self.zoom += (1 - t) * 0.18

        # Shake.

        if 9 <= frame <= 11:

            self.offset_x = random.randint(-3, 3)
            self.offset_y = random.randint(-3, 3)


# ============================================================
# PARTICLES
# ============================================================


class Particle:

    def __init__(self, x, y, vx, vy, radius, color, life):

        self.x = x
        self.y = y

        self.vx = vx
        self.vy = vy

        self.radius = radius

        self.color = color

        self.life = life

        self.max_life = life

    @property
    def alive(self):

        return self.life > 0

    @property
    def alpha(self):

        return int(255 * (self.life / self.max_life))

    def update(self):

        self.x += self.vx
        self.y += self.vy

        self.life -= 1

    def draw(self, img):

        if not self.alive:

            return

        draw = ImageDraw.Draw(img)

        r = self.radius

        draw.ellipse(
            (self.x - r, self.y - r, self.x + r, self.y + r),
            fill=(self.color[0], self.color[1], self.color[2], self.alpha),
        )


# ============================================================
# EMITTER
# ============================================================


class ParticleEmitter:

    def __init__(self, amount=70):

        self.amount = amount

        self.particles = []

        self.reset()

    def reset(self):
        rng = random.Random()
        self.particles.clear()

        for _ in range(self.amount):

            angle = rng.random() * math.pi * 2

            dist = rng.randint(30, 120)

            speed = rng.uniform(0.4, 1.4)

            x = CENTER_X + math.cos(angle) * dist
            y = CENTER_Y + math.sin(angle) * dist

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            color = rng.choice([WHITE, CYAN, GREEN, GOLD])

            self.particles.append(
                Particle(x, y, vx, vy, rng.randint(2, 4), color, rng.randint(30, 55))
            )

    def update(self):

        for p in self.particles:

            p.update()

        self.particles = [p for p in self.particles if p.alive]

    def draw(self, img):

        for p in self.particles:

            p.draw(img)


# ============================================================
# INSTANCES
# ============================================================


CAMERA = Camera()

EMITTER = ParticleEmitter()


TRAINER_SCALE = 0.55


class Trainer:

    def __init__(self, name="red"):

        self.frames = load_trainer(name)

    def frame(self, frame):

        index = min(
            len(self.frames) - 1,
            frame // 1,
        )
        return self.frames[index]

    def draw(self, img, frame):

        trainer = self.frame(frame)

        trainer = trainer.resize(
            (
                int(trainer.width * TRAINER_SCALE),
                int(trainer.height * TRAINER_SCALE),
            ),
            Image.NEAREST,
        )

        img.alpha_composite(
            trainer,
            (-15, HEIGHT - trainer.height + 10),
        )


# ============================================================
# POKEBALL
# ============================================================


class Pokeball:

    def __init__(self, type_name="Pokéball"):

        sprite = load_pokeball(type_name)

        bbox = sprite.getbbox()

        if bbox:
            sprite = sprite.crop(bbox)

        self.sprite_cerrada = sprite.resize((20, 20), Image.LANCZOS)

        filename = (
            type_name.lower().replace("é", "e").replace("-", "_").replace(" ", "_")
        )

        open_sprite = Image.open(POKEBALLS_DIR / f"{filename}_open.png").convert("RGBA")

        bbox = open_sprite.getbbox()

        if bbox:
            open_sprite = open_sprite.crop(bbox)

        self.open_sprite = open_sprite.resize((20, 20), Image.LANCZOS)

        # Current sprite.
        self.sprite = self.sprite_cerrada

        self.frame = 0

        self.reset()

    def reset(self):

        self.x = 170
        self.y = 300

        self.rotation = -40

        self.visible = True

    # --------------------------------------------------------

    def position(self, frame):

        # ---------------------------------
        # Lanzamiento
        # ---------------------------------

        if frame <= 12:

            t = ease_out(frame / 12)

            self.x = lerp(BALL_START_X, CENTER_X, t)

            base_y = lerp(BALL_START_Y, CENTER_Y, t)

            altura = math.sin(t * math.pi) * 120

            self.y = base_y - altura

            # Giro
            self.rotation = lerp(-90, 720, t)

        # ---------------------------------
        # Impact.
        # ---------------------------------

        elif frame <= 14:

            self.x = CENTER_X
            self.y = CENTER_Y + 35

            self.rotation += 25

        # ---------------------------------
        # Fall.
        # ---------------------------------

        elif frame <= 18:

            t = (frame - 14) / 4

            self.x = CENTER_X

            self.y = lerp(CENTER_Y + 25, GROUND_Y, t)
            self.rotation += 15

        # ---------------------------------
        # Rebote
        # ---------------------------------

        elif frame <= 20:

            t = (frame - 18) / 2

            self.x = CENTER_X

            self.y = GROUND_Y - math.sin(t * math.pi) * 18

        # ---------------------------------
        # Espera
        # ---------------------------------

        elif frame < 22:

            self.x = CENTER_X
            self.y = GROUND_Y

        # ---------------------------------
        # Shake 1
        # ---------------------------------

        elif frame < 24:

            self.x = CENTER_X - 12
            self.y = GROUND_Y
            self.rotation = -18

        # ---------------------------------
        # Shake 2
        # ---------------------------------

        elif frame < 26:

            self.x = CENTER_X + 12
            self.y = GROUND_Y
            self.rotation = 18

        # ---------------------------------
        # Shake 3
        # ---------------------------------

        elif frame < 28:

            self.x = CENTER_X - 8
            self.y = GROUND_Y
            self.rotation = -12

        # ---------------------------------
        # Final
        # ---------------------------------

        else:

            self.x = CENTER_X
            self.y = GROUND_Y
            self.rotation = 0

    # --------------------------------------------------------

    def draw(self, img):

        if not self.visible:
            return

        if self.frame <= 2:
            return

        if 12 <= self.frame <= 15:
            ball = self.open_sprite.copy()
        else:
            ball = self.sprite_cerrada.copy()

        ball = ball.rotate(self.rotation, expand=True, resample=Image.BICUBIC)

        img.alpha_composite(
            ball, (int(self.x - ball.width / 2), int(self.y - ball.height / 2))
        )


# ============================================================
# IMPACT FLASH
# ============================================================


class ImpactFlash:

    def draw(self, img, frame):

        if frame < 8 or frame > 11:

            return

        alpha = {8: 80, 9: 180, 10: 120, 11: 40}.get(frame, 0)

        overlay = Image.new("RGBA", img.size, (255, 255, 255, alpha))

        img.alpha_composite(overlay)


# ============================================================
# SPARKS
# ============================================================


class SparkEmitter:

    def draw(self, img, frame):

        if frame < 12:
            return

        if frame > 14:
            return

        draw = ImageDraw.Draw(img)

        rng = random.Random(frame)

        for _ in range(30):

            ang = rng.random() * math.pi * 2

            dist = rng.randint(10, 80)

            IMPACT_Y = CENTER_Y + 35

            x = CENTER_X + math.cos(ang) * dist
            y = IMPACT_Y + math.sin(ang) * dist

            draw.line((CENTER_X, IMPACT_Y, x, y), fill=GOLD, width=2)


# ============================================================
# INSTANCES
# ============================================================


FLASH = ImpactFlash()

SPARKS = SparkEmitter()
# ============================================================
# CAPTURE ANIMATION
# ============================================================


class CaptureAnimation:

    def __init__(
        self,
        sprite_path,
        pokemon_name,
        trainer="red",
        pokeball="Pokéball",
        captured=True,
        type_name=None,
    ):

        self.sprite_frames, self.sprite_durations = load_gif_frames(sprite_path)

        self.sprite_white_frames = [white_sprite(frame) for frame in self.sprite_frames]

        self.sprite_index = 0
        self.sprite_timer = 0
        self.name = pokemon_name

        self.captured = captured
        self.type_name = type_name
        self.frames = []
        self.trainer_name = trainer
        # Store the Poké Ball name.
        self.pokeball = pokeball

        # Create the Poké Ball with that sprite.
        self.pokeball_sprite = Pokeball(self.pokeball)

    # --------------------------------------------------------

    def get_sprite(self, frame, gif_frame):

        original = self.sprite_frames[gif_frame]
        blanco = self.sprite_white_frames[gif_frame]

        # Before impact.

        if frame <= 7:

            return original

        # Fade to white.

        elif frame <= 10:

            t = ease_in_out((frame - 8) / 2)

            return Image.blend(original, blanco, t)

        # Fully white.

        elif frame <= 13:

            return blanco

        # Escaped Pokémon return immediately.

        elif not self.captured:

            return original

        # Captured.

        return blanco

    # --------------------------------------------------------

    def sprite_scale(self, frame):

        scale = 1.0

        # Compression toward the Poké Ball.

        if self.captured and frame >= 12:

            t = ease_out(min(1, (frame - 12) / 4))

            scale = lerp(1.0, 0.15, t)

        return max(0.05, scale)

    # --------------------------------------------------------

    def sprite_alpha(self, frame):

        if not self.captured:

            return 255

        if frame < 12:

            return 255

        t = ease_out(min(1, (frame - 12) / 4))

        return int(lerp(255, 0, t))

    # --------------------------------------------------------

    def sprite_position(self, sprite, frame):

        x = CENTER_X
        y = CENTER_Y + 35

        if self.captured and frame >= 12:

            t = ease_out(min(1, (frame - 12) / 4))

            y = lerp(CENTER_Y + 35, GROUND_Y, t)

        x -= sprite.width // 2
        y -= sprite.height // 2

        x += CAMERA.offset_x
        y += CAMERA.offset_y

        return int(x), int(y)

    # --------------------------------------------------------

    # --------------------------------------------------------

    def render_frame(self, frame):

        CAMERA.update(frame)

        self.pokeball_sprite.frame = frame

        self.pokeball_sprite.position(frame)

        img = BACKGROUND.render(frame)
        img = BACKGROUND.render(frame)

        self.trainer.draw(
            img,
            frame,
        )

        # =====================================
        # Impact particles.
        # =====================================

        if frame == 12:

            EMITTER.reset()

        if frame >= 12:

            EMITTER.update()
            EMITTER.draw(img)

            SPARKS.draw(img, frame)

        self.sprite_timer += FRAME_DURATION

        contador = 0

        while self.sprite_timer >= self.sprite_durations[self.sprite_index]:
            contador += 1

            if contador > 100:
                raise RuntimeError(
                    f"Infinite loop. "
                    f"Frame={self.sprite_index} "
                    f"Duration={self.sprite_durations[self.sprite_index]}"
                )

            self.sprite_timer -= self.sprite_durations[self.sprite_index]

            self.sprite_index = (self.sprite_index + 1) % len(self.sprite_frames)
            self.sprite_timer -= self.sprite_durations[self.sprite_index]

            self.sprite_index = (self.sprite_index + 1) % len(self.sprite_frames)

        gif_frame = self.sprite_index

        sprite = self.get_sprite(frame, gif_frame)
        # Preserve the original GIF size.
        sprite = sprite.copy()

        alpha = self.sprite_alpha(frame)

        sprite = sprite.copy()

        r, g, b, a = sprite.split()

        a = a.point(lambda p: int(p * alpha / 255))

        sprite.putalpha(a)

        x, y = self.sprite_position(sprite, frame)

        img.alpha_composite(sprite, (x, y))

        self.pokeball_sprite.draw(img)

        FLASH.draw(img, frame)

        return img

    # ========================================================

    def render(self):

        global BACKGROUND
        global FLASH
        global SPARKS

        BACKGROUND = Background(self.type_name)
        self.trainer = Trainer(
            self.trainer_name,
        )
        FLASH = ImpactFlash()
        SPARKS = SparkEmitter()

        self.frames.clear()
        self.sprite_index = 0
        self.sprite_timer = 0

        self.pokeball_sprite.reset()

        for frame in range(FPS):

            self.frames.append(self.render_frame(frame))

        # Preserve the final frame.

        final_frame = self.frames[-1]

        for _ in range(4):

            self.frames.append(final_frame.copy())

    # ========================================================

    def save_gif(self, filename=f"captura_{time.time_ns()}.gif"):

        if not self.frames:

            self.render()

        self.frames[0].save(
            filename,
            save_all=True,
            append_images=self.frames[1:],
            duration=FRAME_DURATION,
            loop=0,
            optimize=False,
            disposal=2,
        )

        return filename

    # ========================================================

    def gif_bytes(self):

        if not self.frames:
            self.render()

        buffer = BytesIO()

        self.frames[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=self.frames[1:],
            duration=FRAME_DURATION,
            loop=0,
            optimize=True,
            disposal=2,
        )

        buffer.seek(0)

        return buffer

    # ========================================================

    def png_bytes(self):

        if not self.frames:

            self.render()

        buffer = BytesIO()

        self.frames[0].save(buffer, format="PNG")

        buffer.seek(0)

        return buffer


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    anim = CaptureAnimation(
        sprite_path="https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev/regular/25.gif",
        pokemon_name="Pikachu",
        trainer="leaf",
        pokeball="Poké Ball",
        captured=True,
        type_name="electric",
    )

    anim.render()
    anim.save_gif("captura.gif")
