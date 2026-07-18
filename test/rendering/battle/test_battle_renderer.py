from PIL import Image

from rendering.battle.frame_state import BattleFrameState
from rendering.battle.gif_assets import BattleGifLoader, GifSequence, _decode_gif_bytes
from rendering.battle.hud import BattleFonts
from rendering.battle.layout import DISCORD_MAX_GIF_BYTES
from rendering.battle.renderer import BattleRenderer
from test.rendering.battle.test_sprite_urls import _make_test_gif


class FakeBattleGifLoader(BattleGifLoader):
    def __init__(self) -> None:
        self._opponent = GifSequence(
            frames=(
                Image.new("RGBA", (96, 96), (0, 128, 255, 255)),
            ),
            durations_ms=(100,),
        )
        self._initiator = GifSequence(
            frames=(
                Image.new("RGBA", (96, 96), (255, 128, 0, 255)),
            ),
            durations_ms=(100,),
        )

    def load(self, url: str) -> GifSequence:
        if "/back" in url:
            return self._initiator
        if "/regular" in url or "/shiny" in url:
            return self._opponent
        raise ValueError(url)


def test_battle_renderer_produces_gif_bytes():
    renderer = BattleRenderer(gif_loader=FakeBattleGifLoader())
    frame = BattleFrameState(
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_active_name="Pikachu",
        side_b_active_name="Squirtle",
        side_a_hp=80,
        side_a_hp_max=100,
        side_b_hp=60,
        side_b_hp_max=100,
        side_a_pokeapi_id=25,
        side_b_pokeapi_id=7,
        side_a_shiny=False,
        side_b_shiny=False,
        attack_line="Pikachu used Thunderbolt!",
        turn_number=1,
    )

    background = renderer.get_background_for_battle(42)
    gif_bytes = renderer.render_to_bytes(frame, background=background)

    assert gif_bytes.startswith(b"GIF")


class ManyFrameBattleGifLoader(BattleGifLoader):
    def load(self, url: str) -> GifSequence:
        color = (255, 128, 0, 255) if "/back" in url else (0, 128, 255, 255)
        frames = tuple(
            Image.new("RGBA", (120, 120), color) for _ in range(60)
        )
        return GifSequence(frames=frames, durations_ms=tuple([100] * len(frames)))


def test_battle_renderer_gif_stays_under_discord_limit():
    renderer = BattleRenderer(gif_loader=ManyFrameBattleGifLoader())
    frame = BattleFrameState(
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_active_name="Pikachu",
        side_b_active_name="Squirtle",
        side_a_hp=80,
        side_a_hp_max=100,
        side_b_hp=60,
        side_b_hp_max=100,
        side_a_pokeapi_id=25,
        side_b_pokeapi_id=7,
        side_a_shiny=False,
        side_b_shiny=False,
        attack_line="",
        turn_number=1,
    )

    gif_bytes = renderer.render_to_bytes(
        frame,
        background=renderer.get_background_for_battle(42),
    )

    assert len(gif_bytes) <= DISCORD_MAX_GIF_BYTES


def test_battle_renderer_composes_sprites_and_hud():
    renderer = BattleRenderer(gif_loader=FakeBattleGifLoader())
    frame = BattleFrameState(
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_active_name="Pikachu",
        side_b_active_name="Squirtle",
        side_a_hp=80,
        side_a_hp_max=100,
        side_b_hp=60,
        side_b_hp_max=100,
        side_a_pokeapi_id=25,
        side_b_pokeapi_id=7,
        side_a_shiny=False,
        side_b_shiny=False,
        attack_line="Pikachu used Thunderbolt!",
        turn_number=1,
    )

    background = renderer.get_background_for_battle(42)
    loader = FakeBattleGifLoader()
    opponent = loader.load("https://example.test/regular/7")
    initiator = loader.load("https://example.test/back/25")
    fonts = BattleFonts(
        trainer=renderer._assets.get_font(28),
        pokemon=renderer._assets.get_font(24),
        hp_text=renderer._assets.get_font(20),
    )
    frames, durations = renderer._compose_frames(
        frame,
        base_background=background.copy(),
        opponent_sequence=opponent,
        initiator_sequence=initiator,
        fonts=fonts,
    )

    assert len(frames) == 1
    assert durations == [100]
    assert frames[0].tobytes() != background.convert("RGB").tobytes()


def test_decode_gif_bytes_reads_animation_frames():
    sequence = _decode_gif_bytes(_make_test_gif((255, 0, 0, 255)))

    assert len(sequence.frames) == 1
    assert sequence.durations_ms == (100,)


def test_battle_background_is_stable_for_same_battle_id():
    renderer = BattleRenderer(gif_loader=FakeBattleGifLoader())

    first = renderer.get_background_for_battle(7)
    second = renderer.get_background_for_battle(7)

    assert first.tobytes() == second.tobytes()
