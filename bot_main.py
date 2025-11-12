#!/usr/bin/env python3
"""
Willhaben Apartment Scraper - Telegram Bot

Continuously monitors for new apartment listings and sends notifications via Telegram.
Runs the scraper periodically and notifies about new listings with photos.
"""

import os
import sys
import logging
import signal
import asyncio
from datetime import datetime
from typing import List, Dict

from dotenv import load_dotenv

from src.scheduler import ScraperScheduler
from src.telegram_bot import TelegramNotifier
from src.logger import get_logger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
action_logger = get_logger()


class TelegramBot:
    """Main bot application that coordinates scraping and notifications."""

    def __init__(self):
        """Initialize bot with configuration from environment."""
        # Get Telegram configuration
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            raise ValueError(
                "Missing Telegram configuration. "
                "Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
            )

        # Get scraper configuration
        self.interval_minutes = int(os.getenv('SCRAPER_INTERVAL_MINUTES', '5'))
        self.photos_dir = os.getenv('PHOTOS_DIR', 'photos')
        self.download_photos = os.getenv('DOWNLOAD_PHOTOS', 'true').lower() == 'true'

        # Initialize Telegram notifier
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id)

        # Initialize scheduler with callback
        self.scheduler = ScraperScheduler(
            interval_minutes=self.interval_minutes,
            headless=True,
            download_photos=self.download_photos,
            on_new_listings=self.handle_new_listings,
        )

        logger.info(f"Bot initialized: interval={self.interval_minutes}min, chat={self.chat_id}")
        action_logger.info(f"Telegram bot initialized: interval={self.interval_minutes}min")

    def handle_new_listings(self, new_listings: List[Dict]):
        """
        Handle new listings by sending Telegram notifications.

        Args:
            new_listings: List of new listing dictionaries
        """
        if not new_listings:
            return

        logger.info(f"Processing {len(new_listings)} new listings for Telegram")

        try:
            # Send notifications asynchronously
            sent_count = asyncio.run(
                self.notifier.send_listings(new_listings, self.photos_dir)
            )

            action_logger.info(
                f"Telegram notifications sent: {sent_count}/{len(new_listings)} successful"
            )

        except Exception as e:
            logger.error(f"Error sending Telegram notifications: {e}", exc_info=True)
            action_logger.error("Telegram notification error", e)

    def run(self):
        """Start the bot and run forever."""
        logger.info("=" * 60)
        logger.info("Willhaben Telegram Bot Starting")
        logger.info(f"Scraper interval: {self.interval_minutes} minutes")
        logger.info(f"Photo downloads: {'enabled' if self.download_photos else 'disabled'}")
        logger.info(f"Target chat: {self.chat_id}")
        logger.info("=" * 60)

        # Setup graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.scheduler.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run scheduler
        try:
            self.scheduler.run_forever()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.scheduler.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            action_logger.error("Bot fatal error", e)
            sys.exit(1)


def main():
    """Main entry point."""
    try:
        bot = TelegramBot()
        bot.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
