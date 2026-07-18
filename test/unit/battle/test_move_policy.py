from core.battle.rules.move_policy import (
    MoveData,
    is_valid_ai_move,
    move_data_from_poke_env,
    pick_automatic_move,
)


def test_move_data_from_poke_env_normalizes_fractional_accuracy():
    raw = type(
        "Move",
        (),
        {
            "category": type("Category", (), {"name": "SPECIAL"})(),
            "type": type("MoveType", (), {"name": "electric"})(),
            "base_power": 90,
            "accuracy": 1.0,
            "flags": [],
            "name": "Thunderbolt",
        },
    )()

    move_data = move_data_from_poke_env("thunderbolt", raw)

    assert move_data.category == "Special"
    assert move_data.accuracy == 100
    assert is_valid_ai_move("thunderbolt", move_data)


def test_pick_automatic_move_prefers_stab_special_move():
    learnset = {
        "tackle": MoveData(
            move_id="tackle",
            display_name="Tackle",
            category="Physical",
            move_type="normal",
            base_power=40,
            accuracy=100,
        ),
        "thunderbolt": MoveData(
            move_id="thunderbolt",
            display_name="Thunderbolt",
            category="Special",
            move_type="electric",
            base_power=90,
            accuracy=100,
        ),
    }

    move_id, move_name = pick_automatic_move(
        "pikachu",
        attack=80,
        special_attack=120,
        types=("electric",),
        learnset=learnset,
    )

    assert move_id == "thunderbolt"
    assert move_name == "Thunderbolt"


def test_pick_automatic_move_uses_real_poke_env_thunderbolt():
    from poke_env.battle.move import Move

    move_data = move_data_from_poke_env("thunderbolt", Move("thunderbolt", gen=9))

    assert move_data.accuracy == 100
    assert is_valid_ai_move("thunderbolt", move_data)
