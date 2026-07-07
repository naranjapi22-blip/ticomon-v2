import os

from dotenv import load_dotenv

from interfaces.discord.bot import create_bot


def main():
    load_dotenv()

    bot = create_bot()
    bot.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
