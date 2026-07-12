import logging
import os

from dotenv import load_dotenv

from interfaces.discord.bot import create_bot


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv()

    logger = logging.getLogger(__name__)
    logger.info("Starting TicoMon bot")

    bot = create_bot()
    try:
        bot.run(os.environ["DISCORD_TOKEN"])
    finally:
        logger.info("TicoMon bot process stopped")


if __name__ == "__main__":
    main()
