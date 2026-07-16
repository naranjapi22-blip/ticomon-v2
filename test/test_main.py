from types import SimpleNamespace
from unittest.mock import Mock

import main


def test_main_disables_discord_owned_logging(monkeypatch) -> None:
    bot = SimpleNamespace(run=Mock())
    monkeypatch.setenv("DISCORD_TOKEN", "token")
    monkeypatch.setattr(main, "create_bot", lambda: bot)

    main.main()

    bot.run.assert_called_once_with("token", log_handler=None)
