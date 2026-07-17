from rendering.battle.frame_state import BattleFrameState
from rendering.battle.renderer import BattleRenderer


def test_battle_renderer_produces_png_bytes():
    renderer = BattleRenderer()
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
    png_bytes = renderer.render_to_bytes(frame, background=background)

    assert png_bytes.startswith(b"\x89PNG")


def test_battle_renderer_places_sprite_content_on_canvas():
    from PIL import ImageChops

    renderer = BattleRenderer()
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
    rendered = renderer.render(frame, background=background.copy())
    diff = ImageChops.difference(rendered, background)

    assert diff.getbbox() is not None


def test_battle_background_is_stable_for_same_battle_id():
    renderer = BattleRenderer()

    first = renderer.get_background_for_battle(7)
    second = renderer.get_background_for_battle(7)

    assert first.tobytes() == second.tobytes()
