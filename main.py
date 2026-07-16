import logging
import os

from dotenv import load_dotenv

from interfaces.discord.bot import create_bot


def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("ticomon.startup").setLevel(logging.INFO)

    load_dotenv()

    bot = create_bot()
    bot.run(os.environ["DISCORD_TOKEN"], log_handler=None)


if __name__ == "__main__":
    main()
