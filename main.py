import logging
import asyncio
import os
from telegram.ext import Application
from dotenv import load_dotenv
from handlers import BotHandlers
import nest_asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE") or None
COOKIES_FROM_BROWSER = os.getenv("COOKIES_FROM_BROWSER") or None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot."""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return

    # Create application with increased timeouts
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(20.0)
        .read_timeout(20.0)
        .write_timeout(20.0)
        .pool_timeout(20.0)
        .build()
    )

    # Initialize handlers
    bot_handlers = BotHandlers(
        ADMIN_ID, cookies_file=COOKIES_FILE, cookies_from_browser=COOKIES_FROM_BROWSER
    )

    # Add handlers
    for handler in bot_handlers.get_handlers():
        application.add_handler(handler)

    # Log startup
    logger.info("Bot started successfully")

    # Start polling
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
