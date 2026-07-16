from types import SimpleNamespace

from interfaces.discord.evolution_sender import _achievement_text


def test_evolution_notification_includes_nature_mint_reward() -> None:
    result = SimpleNamespace(
        achievements=(
            SimpleNamespace(
                achievement_id="first_evolution",
                rewarded_candies={},
                rewarded_mints=1,
            ),
        )
    )

    assert "Nature Mint +1" in _achievement_text(result)
