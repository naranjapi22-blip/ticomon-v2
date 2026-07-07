"""
============================================================

TicoMon Animation Engine
animacion_captura.py

Versión 1.0

Motor de animaciones para capturas.

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
    ImageFilter,
    ImageFont,
    ImageSequence,
)

BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

FONDOS_DIR = ASSETS_DIR / "fondos"

POKEBALLS_DIR = ASSETS_DIR / "pokeballs"

FONTS_DIR = ASSETS_DIR / "fonts"

# ============================================================
# CONFIGURACIÓN
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
# COLORES
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
# FUENTES
# ============================================================


def load_font(size):
    try:
        return ImageFont.truetype(
            str(FONTS_DIR / "DejaVuSans-Bold.ttf"),
            size,
        )
    except Exception:
        return ImageFont.load_default()


TITLE_FONT = load_font(34)
TEXT_FONT = load_font(22)

# ============================================================
# UTILIDADES
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


def cargar_sprite(ruta):

    ruta = Path(ruta)

    if not ruta.exists():

        raise FileNotFoundError(ruta)

    return Image.open(ruta).convert("RGBA")


def cargar_frames_gif(ruta, size=SPRITE_SIZE):

    if str(ruta).startswith("http"):

        print(ruta)

        from urllib.error import HTTPError
        from urllib.request import Request, urlopen

        try:

            req = Request(ruta, headers={"User-Agent": "Mozilla/5.0"})

            with urlopen(req) as response:

                gif = Image.open(BytesIO(response.read()))

        except HTTPError as e:

            if e.code != 404:
                raise

            ruta = ruta.replace("/shiny/", "/regular/")

            print("Fallback:", ruta)

            req = Request(ruta, headers={"User-Agent": "Mozilla/5.0"})

            with urlopen(req) as response:

                gif = Image.open(BytesIO(response.read()))

    else:

        ruta = Path(ruta)

        if not ruta.exists():
            raise FileNotFoundError(ruta)

        gif = Image.open(ruta)

    frames = []
    duraciones = []

    for frame in ImageSequence.Iterator(gif):

        img = frame.convert("RGBA")

        bbox = img.getbbox()

        if bbox:
            img = img.crop(bbox)

        frames.append(img)

        duracion = frame.info.get("duration", 80)

        # Algunos GIF tienen duración 0 ms
        if not duracion or duracion <= 0:
            duracion = 80

        duraciones.append(duracion)

    return frames, duraciones


def cargar_pokeball(tipo):
    archivo = tipo.lower().replace("é", "e").replace(" ", "_") + ".png"

    print("Cargando:", archivo)

    return Image.open(POKEBALLS_DIR / archivo).convert("RGBA")


def sprite_blanco(sprite):

    alpha = sprite.getchannel("A")

    blanco = Image.new("RGBA", sprite.size, WHITE)

    blanco.putalpha(alpha)

    return blanco


def redimensionar(sprite, size):

    escala = min(size / sprite.width, size / sprite.height)

    return sprite.resize(
        (int(sprite.width * escala), int(sprite.height * escala)), Image.LANCZOS
    )


# ============================================================
# FONDO
# ============================================================


class Background:

    def __init__(self, tipo=None):

        if tipo:

            ruta = FONDOS_DIR / f"{tipo}.png"

            if ruta.exists():

                self.background = Image.open(ruta).convert("RGBA")

            else:

                ruta = random.choice(list(FONDOS_DIR.glob("*.png")))

                self.background = Image.open(ruta).convert("RGBA")

        else:

            ruta = random.choice(list(FONDOS_DIR.glob("*.png")))

            self.background = Image.open(ruta).convert("RGBA")

        self.background = self.background.resize((WIDTH, HEIGHT), Image.NEAREST)

    def render(self, frame):

        return self.background.copy()


BACKGROUND = Background()
# ============================================================
# HALO
# ============================================================


class Halo:

    def draw(self, img, frame):

        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))

        draw = ImageDraw.Draw(capa)

        radio = 110 + math.sin(frame * 0.30) * 6

        draw.ellipse(
            (CENTER_X - radio, CENTER_Y - radio, CENTER_X + radio, CENTER_Y + radio),
            fill=(CYAN[0], CYAN[1], CYAN[2], 70),
        )

        capa = capa.filter(ImageFilter.GaussianBlur(35))

        img.alpha_composite(capa)


# ============================================================
# GLOW
# ============================================================


class Glow:

    def __init__(self):

        self.cache = {}

    def draw(self, img, sprite, x, y):

        key = ((sprite.width // 8) * 8, (sprite.height // 8) * 8)

        if key not in self.cache:

            glow = Image.new("RGBA", sprite.size, (CYAN[0], CYAN[1], CYAN[2], 180))

            glow.putalpha(sprite.getchannel("A"))

            glow = glow.filter(ImageFilter.GaussianBlur(3))

            self.cache[key] = glow

        img.alpha_composite(self.cache[key], (x, y))


# ============================================================
# SOMBRA
# ============================================================


class Shadow:

    def draw(self, img, x, y, sprite, frame):

        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))

        draw = ImageDraw.Draw(capa)

        mover = math.sin(frame * 0.30) * 4

        centro_x = x + sprite.width // 2
        base_y = y + sprite.height - 6

        ancho = sprite.width * 0.40
        alto = 10

        draw.ellipse(
            (centro_x - ancho, base_y + mover, centro_x + ancho, base_y + alto + mover),
            fill=(0, 0, 0, 120),
        )

        capa = capa.filter(ImageFilter.GaussianBlur(10))

        img.alpha_composite(capa)


# ============================================================
# CÁMARA
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

        # pequeño zoom durante el impacto

        if 8 <= frame <= 13:

            t = ease_out((frame - 8) / 5)

            self.zoom += t * 0.18

        elif frame > 13:

            t = ease_out(min(1, (frame - 13) / 5))

            self.zoom += (1 - t) * 0.18

        # sacudida

        if 9 <= frame <= 11:

            self.offset_x = random.randint(-3, 3)
            self.offset_y = random.randint(-3, 3)


# ============================================================
# PARTÍCULAS
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
# EMISOR
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
# INSTANCIAS
# ============================================================

HALO = Halo()

GLOW = Glow()

SHADOW = Shadow()

CAMERA = Camera()

EMITTER = ParticleEmitter()
# ============================================================
# POKEBALL
# ============================================================


class Pokeball:

    def __init__(self, tipo="Pokéball"):

        sprite = cargar_pokeball(tipo)

        bbox = sprite.getbbox()

        if bbox:
            sprite = sprite.crop(bbox)

        self.sprite_cerrada = sprite.resize((20, 20), Image.LANCZOS)

        archivo = tipo.lower().replace("é", "e").replace("-", "_").replace(" ", "_")

        sprite_abierta = Image.open(POKEBALLS_DIR / f"{archivo}_open.png").convert(
            "RGBA"
        )

        bbox = sprite_abierta.getbbox()

        if bbox:
            sprite_abierta = sprite_abierta.crop(bbox)

        self.sprite_abierta = sprite_abierta.resize((20, 20), Image.LANCZOS)

        # Sprite actual
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
        # Impacto
        # ---------------------------------

        elif frame <= 14:

            self.x = CENTER_X
            self.y = CENTER_Y + 35

            self.rotation += 25

        # ---------------------------------
        # Caída
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

        if 12 <= self.frame <= 15:
            ball = self.sprite_abierta.copy()
        else:
            ball = self.sprite_cerrada.copy()

        ball = ball.rotate(self.rotation, expand=True, resample=Image.BICUBIC)

        img.alpha_composite(
            ball, (int(self.x - ball.width / 2), int(self.y - ball.height / 2))
        )


# ============================================================
# DESTELLO DEL IMPACTO
# ============================================================


class ImpactFlash:

    def draw(self, img, frame):

        if frame < 8 or frame > 11:

            return

        alpha = {8: 80, 9: 180, 10: 120, 11: 40}.get(frame, 0)

        overlay = Image.new("RGBA", img.size, (255, 255, 255, alpha))

        img.alpha_composite(overlay)


# ============================================================
# CHISPAS
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
# INSTANCIAS
# ============================================================


FLASH = ImpactFlash()

SPARKS = SparkEmitter()
# ============================================================
# CAPTURE ANIMATION
# ============================================================


class CaptureAnimation:
    def __init__(
        self, sprite_path, pokemon_name, pokeball="Pokéball", capturado=True, tipo=None
    ):

        self.sprite_frames, self.sprite_duraciones = cargar_frames_gif(sprite_path)

        self.sprite_white_frames = [
            sprite_blanco(frame) for frame in self.sprite_frames
        ]

        self.sprite_index = 0
        self.sprite_timer = 0
        self.nombre = pokemon_name

        self.capturado = capturado
        self.tipo = tipo
        self.frames = []

        # Guardar el nombre de la Poké Ball
        self.pokeball = pokeball

        # Crear la Poké Ball con ese sprite
        print(f"Poké Ball recibida: '{self.pokeball}'")
        self.pokeball_sprite = Pokeball(self.pokeball)

    # --------------------------------------------------------

    def sprite_actual(self, frame, gif_frame):

        original = self.sprite_frames[gif_frame]
        blanco = self.sprite_white_frames[gif_frame]

        # Antes del impacto

        if frame <= 7:

            return original

        # Se vuelve blanco

        elif frame <= 10:

            t = ease_in_out((frame - 8) / 2)

            return Image.blend(original, blanco, t)

        # Totalmente blanco

        elif frame <= 13:

            return blanco

        # Si escapó vuelve inmediatamente

        elif not self.capturado:

            return original

        # Capturado

        return blanco

    # --------------------------------------------------------

    def sprite_scale(self, frame):

        escala = 1.0

        # Compresión hacia la Poké Ball

        if self.capturado and frame >= 12:

            t = ease_out(min(1, (frame - 12) / 4))

            escala = lerp(1.0, 0.15, t)

        return max(0.05, escala)

    # --------------------------------------------------------

    def sprite_alpha(self, frame):

        if not self.capturado:

            return 255

        if frame < 12:

            return 255

        t = ease_out(min(1, (frame - 12) / 4))

        return int(lerp(255, 0, t))

    # --------------------------------------------------------

    def sprite_position(self, sprite, frame):

        x = CENTER_X
        y = CENTER_Y + 35

        if self.capturado and frame >= 12:

            t = ease_out(min(1, (frame - 12) / 4))

            y = lerp(CENTER_Y + 35, GROUND_Y, t)

        x -= sprite.width // 2
        y -= sprite.height // 2

        x += CAMERA.offset_x
        y += CAMERA.offset_y

        return int(x), int(y)

    # --------------------------------------------------------

    def draw_text(self, img, frame):

        draw = ImageDraw.Draw(img)

        if frame < 19:

            texto = "Throwing Poké Ball..."

        elif self.capturado:

            texto = f"{self.nombre.capitalize()} was caught!"

        else:

            texto = f"{self.nombre.capitalize()} escaped!"

        bbox = draw.textbbox((0, 0), texto, font=TEXT_FONT)

        draw.text(
            ((WIDTH - (bbox[2] - bbox[0])) // 2, HEIGHT - 30),
            texto,
            font=TEXT_FONT,
            fill=WHITE,
        )

    # --------------------------------------------------------

    def render_frame(self, frame):

        CAMERA.update(frame)

        self.pokeball_sprite.frame = frame

        self.pokeball_sprite.position(frame)

        img = BACKGROUND.render(frame)

        HALO.draw(img, frame)
        # =====================================
        # Partículas del impacto
        # =====================================

        if frame == 12:

            EMITTER.reset()

        if frame >= 12:

            EMITTER.update()

            EMITTER.draw(img)

        SPARKS.draw(img, frame)

        self.sprite_timer += FRAME_DURATION

        contador = 0

        while self.sprite_timer >= self.sprite_duraciones[self.sprite_index]:
            contador += 1

            if contador > 100:
                raise RuntimeError(
                    f"Bucle infinito. "
                    f"Frame={self.sprite_index} "
                    f"Duración={self.sprite_duraciones[self.sprite_index]}"
                )

            self.sprite_timer -= self.sprite_duraciones[self.sprite_index]

            self.sprite_index = (self.sprite_index + 1) % len(self.sprite_frames)
            self.sprite_timer -= self.sprite_duraciones[self.sprite_index]

            self.sprite_index = (self.sprite_index + 1) % len(self.sprite_frames)

        gif_frame = self.sprite_index

        sprite = self.sprite_actual(frame, gif_frame)
        # Mantener el tamaño original del GIF
        sprite = sprite.copy()

        alpha = self.sprite_alpha(frame)

        sprite = sprite.copy()

        r, g, b, a = sprite.split()

        a = a.point(lambda p: int(p * alpha / 255))

        sprite.putalpha(a)

        x, y = self.sprite_position(sprite, frame)
        SHADOW.draw(img, x, y, sprite, frame)

        img.alpha_composite(sprite, (x, y))

        self.pokeball_sprite.draw(img)

        FLASH.draw(img, frame)

        self.draw_text(img, frame)

        return img

    # ========================================================

    def render(self):

        global BACKGROUND
        global HALO
        global GLOW
        global SHADOW
        global FLASH
        global SPARKS

        BACKGROUND = Background(self.tipo)

        HALO = Halo()
        GLOW = Glow()
        SHADOW = Shadow()
        FLASH = ImpactFlash()
        SPARKS = SparkEmitter()

        self.frames.clear()

        self.sprite_index = 0
        self.sprite_timer = 0

        self.pokeball_sprite.reset()

        for frame in range(FPS):

            self.frames.append(self.render_frame(frame))

        # Mantener el último frame

        ultimo = self.frames[-1]

        for _ in range(12):

            self.frames.append(ultimo.copy())

        return self.frames

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

        print("Frames:", len(self.frames))
        print("Resolución:", self.frames[0].size)
        print("Duración:", FRAME_DURATION)
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
        capturado=True,
    )

    anim.render()
    anim.save_gif("captura.gif")

    print("✅ GIF de captura generado correctamente.")
