from types import SimpleNamespace

from application.achievement.query_service import ACHIEVEMENT_PRESENTATION
from interfaces.discord.achievement_notifications import format_unlocks


def _unlock(amount: int):
    return SimpleNamespace(
        achievement_id="achievement",
        rewarded_candies={},
        rewarded_mints=amount,
    )


def test_nature_mint_notification_uses_singular_and_plural() -> None:
    assert "Nature Mint +1" in format_unlocks((_unlock(1),))
    assert "Nature Mints +2" in format_unlocks((_unlock(2),))


def test_historical_safari_id_is_presented_as_500_captures() -> None:
    name, description = ACHIEVEMENT_PRESENTATION["safari_captures_50"]

    assert name == "Safari Captures 500"
    assert "500" in description
