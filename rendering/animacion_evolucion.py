"""
============================================================

TicoMon Animation Engine
animacion_evolucion.py

Versión 2.0

Motor de animaciones para:

- Evoluciones
- Eclosiones
- Shiny
- Incursiones
- Eventos especiales

============================================================
"""

from __future__ import annotations

import math
import random
from io import BytesIO
from pathlib import Path

from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont,
)

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

WIDTH = 800
HEIGHT = 450

CENTER_X = WIDTH // 2
CENTER_Y = 190

FPS = 24
FRAME_DURATION = 70

SPRITE_SIZE = 280

# ============================================================
# COLORES
# ============================================================

BACKGROUND_TOP = (15, 25, 80)

BACKGROUND_BOTTOM = (55, 20, 110)

WHITE = (255, 255, 255)

BLACK = (0, 0, 0)

GOLD = (255, 220, 60)

CYAN = (120, 220, 255)

BLUE = (70, 170, 255)

PURPLE = (180, 120, 255)

# ============================================================
# FUENTES
# ============================================================


def load_font(size: int):

    posibles_fuentes = [
        Path("fonts/DejaVuSans-Bold.ttf"),
        Path("assets/fonts/DejaVuSans-Bold.ttf"),
        Path("DejaVuSans-Bold.ttf"),
        Path("arial.ttf"),
    ]

    for fuente in posibles_fuentes:

        try:
            return ImageFont.truetype(str(fuente), size)
        except Exception:
            continue

    return ImageFont.load_default()


TITLE_FONT = load_font(34)
TEXT_FONT = load_font(22)

# ============================================================
# UTILIDADES
# ============================================================


def lerp(a, b, t):

    return a + (b - a) * t


def clamp(valor, minimo, maximo):

    return max(minimo, min(valor, maximo))


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


def sprite_blanco(sprite):

    alpha = sprite.getchannel("A")

    blanco = Image.new("RGBA", sprite.size, WHITE)

    blanco.putalpha(alpha)

    return blanco


def redimensionar(sprite, size):

    return sprite.resize((size, size), Image.LANCZOS)


# ============================================================
# FONDO
# ============================================================


class Background:

    def __init__(self):

        self.stars = []

        for _ in range(90):

            self.stars.append(
                {
                    "x": random.randint(0, WIDTH),
                    "y": random.randint(0, HEIGHT),
                    "size": random.randint(1, 3),
                    "alpha": random.randint(120, 255),
                }
            )

    def draw_gradient(self):

        img = Image.new("RGBA", (WIDTH, HEIGHT))

        draw = ImageDraw.Draw(img)

        for y in range(HEIGHT):

            t = y / HEIGHT

            r = int(lerp(BACKGROUND_TOP[0], BACKGROUND_BOTTOM[0], t))
            g = int(lerp(BACKGROUND_TOP[1], BACKGROUND_BOTTOM[1], t))
            b = int(lerp(BACKGROUND_TOP[2], BACKGROUND_BOTTOM[2], t))

            draw.line((0, y, WIDTH, y), fill=(r, g, b))

        return img

    def draw_nebula(self, img):

        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))

        draw = ImageDraw.Draw(capa)

        colores = [(70, 170, 255, 25), (180, 120, 255, 20), (120, 220, 255, 18)]

        for color in colores:

            x = random.randint(80, WIDTH - 80)
            y = random.randint(60, HEIGHT - 60)

            r = random.randint(90, 170)

            draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

        capa = capa.filter(ImageFilter.GaussianBlur(80))

        img.alpha_composite(capa)

    def draw_stars(self, img, frame):

        draw = ImageDraw.Draw(img)

        for star in self.stars:

            brillo = star["alpha"]

            brillo += int(math.sin(frame * 0.15 + star["x"]) * 20)

            brillo = clamp(brillo, 80, 255)

            r = star["size"]

            draw.ellipse(
                (star["x"] - r, star["y"] - r, star["x"] + r, star["y"] + r),
                fill=(255, 255, 255, brillo),
            )

    def render(self, frame):

        img = self.draw_gradient()

        self.draw_nebula(img)

        self.draw_stars(img, frame)

        return img


# ============================================================
# HALO
# ============================================================


class Halo:

    def draw(self, img, frame):

        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))

        draw = ImageDraw.Draw(capa)

        radio = 130

        radio += math.sin(frame * 0.35) * 8

        draw.ellipse(
            (CENTER_X - radio, CENTER_Y - radio, CENTER_X + radio, CENTER_Y + radio),
            fill=(CYAN[0], CYAN[1], CYAN[2], 70),
        )

        capa = capa.filter(ImageFilter.GaussianBlur(45))

        img.alpha_composite(capa)


# ============================================================
# ARO DE ENERGÍA
# ============================================================


class EnergyRing:

    def draw(self, img, frame):

        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))

        draw = ImageDraw.Draw(capa)

        giro = frame * 6

        for offset in (0, 18, 36):

            radio = 128 + offset

            inicio = giro + offset

            fin = inicio + 250

            draw.arc(
                (
                    CENTER_X - radio,
                    CENTER_Y - radio,
                    CENTER_X + radio,
                    CENTER_Y + radio,
                ),
                start=inicio,
                end=fin,
                fill=CYAN,
                width=4,
            )

        capa = capa.filter(ImageFilter.GaussianBlur(2))

        img.alpha_composite(capa)


# ============================================================
# SOMBRA
# ============================================================


class Shadow:

    def draw(self, img, frame):

        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))

        draw = ImageDraw.Draw(capa)

        mover = math.sin(frame * 0.35) * 4

        draw.ellipse(
            (
                CENTER_X - 70,
                CENTER_Y + 90 + mover,
                CENTER_X + 70,
                CENTER_Y + 108 + mover,
            ),
            fill=(0, 0, 0, 120),
        )

        capa = capa.filter(ImageFilter.GaussianBlur(12))

        img.alpha_composite(capa)


# ============================================================
# INSTANCIAS
# ============================================================

BACKGROUND = Background()

HALO = Halo()

ENERGY_RING = EnergyRing()

SHADOW = Shadow()
# ============================================================
# PARTÍCULA
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

    def __init__(self, amount=80):

        self.amount = amount

        self.particles = []

        self.reset()

    def reset(self):

        self.particles.clear()

        for _ in range(self.amount):

            angle = random.random() * math.pi * 2

            distance = random.randint(60, 160)

            speed = random.uniform(0.3, 1.2)

            x = CENTER_X + math.cos(angle) * distance
            y = CENTER_Y + math.sin(angle) * distance

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            color = random.choice([WHITE, GOLD, CYAN, PURPLE])

            self.particles.append(
                Particle(
                    x, y, vx, vy, random.randint(2, 4), color, random.randint(35, 60)
                )
            )

    def update(self, frame):

        for p in self.particles:

            p.update()

        self.particles = [p for p in self.particles if p.alive]

        while len(self.particles) < self.amount:

            angle = random.random() * math.pi * 2

            distance = random.randint(50, 160)

            speed = random.uniform(0.3, 1.4)

            x = CENTER_X + math.cos(angle) * distance
            y = CENTER_Y + math.sin(angle) * distance

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            if frame >= 12:

                vx *= 2
                vy *= 2

            color = random.choice([WHITE, CYAN, GOLD])

            self.particles.append(
                Particle(
                    x, y, vx, vy, random.randint(2, 4), color, random.randint(30, 50)
                )
            )

    def draw(self, img):

        for p in self.particles:

            p.draw(img)


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

        # Respiración suave
        self.zoom += math.sin(frame * 0.18) * 0.02

        # Zoom dramático
        if 8 <= frame <= 16:

            t = ease_out((frame - 8) / 8)

            self.zoom += t * 0.30

        elif frame > 16:

            t = ease_out(min(1, (frame - 16) / 6))

            self.zoom += (1 - t) * 0.30

        # Temblor
        if 13 <= frame <= 18:

            self.offset_x = random.randint(-4, 4)

            self.offset_y = random.randint(-4, 4)


# ============================================================
# GLOW
# ============================================================


class Glow:

    def draw(self, img, sprite, x, y):

        glow = sprite.copy()

        alpha = glow.getchannel("A")

        glow = Image.new("RGBA", glow.size, (CYAN[0], CYAN[1], CYAN[2], 170))

        glow.putalpha(alpha)

        glow = glow.filter(ImageFilter.GaussianBlur(10))

        img.alpha_composite(glow, (x, y))


# ============================================================
# INSTANCIAS
# ============================================================

EMITTER = ParticleEmitter()

CAMERA = Camera()

GLOW = Glow()
# ============================================================
# EVOLUTION ANIMATION
# ============================================================


class EvolutionAnimation:

    def __init__(self, sprite_from, sprite_to, pokemon_from, pokemon_to, shiny=False):

        self.sprite_from = cargar_sprite(sprite_from)

        self.sprite_to = cargar_sprite(sprite_to)

        self.sprite_white = sprite_blanco(self.sprite_from)

        self.pokemon_from = pokemon_from

        self.pokemon_to = pokemon_to

        self.shiny = shiny

        self.frames = []

    # ========================================================

    def sprite_actual(self, frame):

        # 0-8
        if frame <= 8:

            return self.sprite_from

        # 9-13
        elif frame <= 13:

            t = ease_in_out((frame - 9) / 4)

            return Image.blend(self.sprite_from, self.sprite_white, t)

        # 14-17
        elif frame <= 17:

            return self.sprite_white

        # 18-23
        else:

            t = ease_in_out((frame - 18) / 5)

            return Image.blend(self.sprite_white, self.sprite_to, t)

    # ========================================================

    def sprite_size(self, frame):

        escala = 1

        escala += math.sin(frame * 0.25) * 0.05

        if 11 <= frame <= 17:

            escala += 0.20

        return int(SPRITE_SIZE * escala * CAMERA.zoom)

    # ========================================================

    def sprite_rotation(self, frame):

        if 12 <= frame <= 18:

            return math.sin(frame * 3) * 5

        return 0

    # ========================================================

    def sprite_position(self, sprite, frame):

        x = CENTER_X - sprite.width // 2

        y = CENTER_Y - sprite.height // 2

        if 13 <= frame <= 18:

            x += random.randint(-5, 5)
            y += random.randint(-5, 5)

        else:

            y += int(math.sin(frame * 0.30) * 8)

        x += CAMERA.offset_x
        y += CAMERA.offset_y

        return x, y

    # ========================================================

    def draw_flash(self, img, frame):

        if frame < 10:

            return

        alpha = {
            10: 30,
            11: 70,
            12: 140,
            13: 255,
            14: 255,
            15: 180,
            16: 90,
            17: 40,
        }.get(frame, 0)

        if alpha == 0:

            return

        overlay = Image.new("RGBA", img.size, (255, 255, 255, alpha))

        img.alpha_composite(overlay)

    # ========================================================

    def draw_text(self, img, frame):

        draw = ImageDraw.Draw(img)

        titulo = "⭐ EVOLUCIÓN ⭐"

        bbox = draw.textbbox((0, 0), titulo, font=TITLE_FONT)

        draw.text(
            ((WIDTH - (bbox[2] - bbox[0])) // 2, 22), titulo, font=TITLE_FONT, fill=GOLD
        )

        if frame < 20:

            puntos = "." * ((frame % 4) + 1)

            texto = f"{self.pokemon_from}" f" está evolucionando" f"{puntos}"

        else:

            texto = f"✨ " f"{self.pokemon_to}" f" apareció"

        bbox = draw.textbbox((0, 0), texto, font=TEXT_FONT)

        draw.text(
            ((WIDTH - (bbox[2] - bbox[0])) // 2, 398), texto, font=TEXT_FONT, fill=WHITE
        )

    # ============================================================
    # RENDER
    # ============================================================

    def render_frame(self, frame):

        CAMERA.update(frame)

        EMITTER.update(frame)

        # -----------------------------
        # Fondo
        # -----------------------------

        img = BACKGROUND.render(frame)

        # -----------------------------
        # Halo
        # -----------------------------

        HALO.draw(img, frame)

        # -----------------------------
        # Aros
        # -----------------------------

        ENERGY_RING.draw(img, frame)

        # -----------------------------
        # Partículas
        # -----------------------------

        EMITTER.draw(img)

        # -----------------------------
        # Sombra
        # -----------------------------

        SHADOW.draw(img, frame)

        # -----------------------------
        # Sprite
        # -----------------------------

        sprite = self.sprite_actual(frame)

        lado = self.sprite_size(frame)

        sprite = redimensionar(sprite, lado)

        sprite = sprite.rotate(
            self.sprite_rotation(frame), resample=Image.BICUBIC, expand=True
        )

        x, y = self.sprite_position(sprite, frame)

        GLOW.draw(img, sprite, x, y)

        img.alpha_composite(sprite, (int(x), int(y)))

        # -----------------------------
        # Flash
        # -----------------------------

        self.draw_flash(img, frame)

        # -----------------------------
        # Texto
        # -----------------------------

        self.draw_text(img, frame)

        return img

    # ========================================================

    def render(self):

        self.frames.clear()

        EMITTER.reset()

        for frame in range(FPS):

            self.frames.append(self.render_frame(frame))

        # Mantener el último frame visible
        ultimo = self.frames[-1]

        for _ in range(12):
            self.frames.append(ultimo.copy())

        return self.frames

    # ========================================================

    def save_gif(self, filename="evolucion.gif"):

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
            optimize=False,
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
# FACTORY
# ============================================================


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    anim = EvolutionAnimation(
        sprite_from="sprites/regular/25.png",
        sprite_to="sprites/regular/26.png",
        pokemon_from="Pikachu",
        pokemon_to="Raichu",
    )

    anim.render()

    anim.save_gif()

    print("✅ GIF generado correctamente.")
