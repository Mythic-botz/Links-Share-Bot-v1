import asyncio
import sys
import time
import signal  # Added missing import
from datetime import datetime
from pyrogram import Client
from pyrogram.enums import ParseMode
from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, PORT, OWNER_ID
from plugins import web_server
import pyrogram.utils
from aiohttp import web

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

name = """
Links Sharing Started
"""

# Flag to control restart loop
RUNNING = True
MAX_RESTART_ATTEMPTS = 3  # Maximum number of restart attempts
RESTART_DELAY = 180  # Delay between restarts (3 minutes in seconds)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN,
        )
        self.LOGGER = LOGGER

    async def start(self, *args, **kwargs):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        # Notify owner of bot restart
        try:
            await self.send_message(
                chat_id=OWNER_ID,
                text="<b><blockquote>🤖 Bot Restarted ♻️</blockquote></b>",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            self.LOGGER(__name__).warning(f"Failed to notify owner ({OWNER_ID}) of bot start: {e}")

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info("Bot Running..!\n\nCreated by \nhttps://t.me/ProObito")
        self.LOGGER(__name__).info(f"{name}")
        self.username = usr_bot_me.username

        # Web-response
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            bind_address = "0.0.0.0"
            await web.TCPSite(app, bind_address, PORT).start()
            self.LOGGER(__name__).info(f"Web server started on {bind_address}:{PORT}")
        except Exception as e:
            self.LOGGER(__name__).error(f"Failed to start web server: {e}")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

# Global cancel flag for broadcast
is_canceled = False
cancel_lock = asyncio.Lock()

# Handle SIGTERM and SIGINT for graceful shutdown
def handle_shutdown(signum, frame):
    global RUNNING
    LOGGER(__name__).info(f"Received signal {signum}, shutting down gracefully...")
    RUNNING = False
    sys.exit(0)  # Exit with 0 to allow Render to restart the container

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# Main function to run the bot with restart logic
def run_bot():
    global RUNNING
    restart_count = 0

    while RUNNING and restart_count < MAX_RESTART_ATTEMPTS:
        try:
            LOGGER(__name__).info(f"Starting bot (Attempt {restart_count + 1}/{MAX_RESTART_ATTEMPTS})...")
            bot = Bot()
            bot.run()  # Blocks until the bot stops
        except Exception as e:
            LOGGER(__name__).error(f"Bot crashed with error: {e}. Attempting restart...")
        finally:
            LOGGER(__name__).info("Bot stopped.")
        
        if RUNNING and restart_count < MAX_RESTART_ATTEMPTS - 1:
            restart_count += 1
            LOGGER(__name__).info(f"Waiting {RESTART_DELAY} seconds before restart attempt {restart_count + 1}...")
            time.sleep(RESTART_DELAY)
        else:
            LOGGER(__name__).info("Max restart attempts reached or bot stopped intentionally.")
            break

    if restart_count >= MAX_RESTART_ATTEMPTS:
        LOGGER(__name__).error("Bot stopped after reaching maximum restart attempts.")
    LOGGER(__name__).info("Bot has fully stopped.")
    sys.exit(0)  # Exit to allow Render to restart the container

if __name__ == "__main__":
    run_bot()