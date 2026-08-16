import asyncio
import logging
import sys
import discord
from ticketbot.config import load_config
from ticketbot.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ticketbot")


async def run():
    cfg = load_config()
    await init_db(cfg.database_path)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        log.info(f"Logged in as {client.user} (id: {client.user.id})")

    try:
        await client.start(cfg.discord_token)
    except KeyboardInterrupt:
        await client.close()


def main():
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        log.info("Exiting")
        sys.exit(0)


if __name__ == "__main__":
    main()
