"""
Telegram bot module for sending apartment listing notifications.

This module handles:
- Sending formatted messages with listing details
- Sending photos for listings
- Message formatting and truncation
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.error import TelegramError

from src.logger import get_logger

logger = get_logger()


class TelegramNotifier:
    """Handles sending notifications to Telegram channel/chat."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot API token
            chat_id: Channel or chat ID to send messages to
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        logger.info(f"Telegram notifier initialized for chat {chat_id}")

    def format_listing_message(self, listing: Dict) -> str:
        """
        Format listing data into a readable message.

        Args:
            listing: Dictionary with listing data (id, listing_name, price, address, apart_size, link)

        Returns:
            Formatted message string
        """
        # Clean and prepare fields
        name = listing.get('listing_name', 'N/A')
        price = listing.get('price', 'N/A')
        address = listing.get('address', 'N/A')
        size = listing.get('apart_size', 'N/A')
        link = listing.get('link', '')

        # Build message
        message = f"🏠 <b>New Apartment Listing</b>\n\n"
        message += f"<b>Name:</b> {name}\n"
        message += f"<b>Price:</b> {price}\n"
        message += f"<b>Address:</b> {address}\n"
        message += f"<b>Size:</b> {size}\n"
        message += f"\n<a href='{link}'>View Listing</a>"

        return message

    async def send_listing(self, listing: Dict, photos_dir: Optional[str] = None) -> bool:
        """
        Send a single listing notification with photos if available.

        Args:
            listing: Dictionary with listing data
            photos_dir: Base directory where photos are stored (default: 'photos')

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            message = self.format_listing_message(listing)

            # Try to send with photos if available
            photo_paths = self._get_listing_photos(listing.get('link', ''), photos_dir)

            if photo_paths:
                # Telegram supports up to 10 photos in a media group
                photos_to_send = photo_paths[:10]

                # Create media group with all photos
                media_group = []
                for i, photo_path in enumerate(photos_to_send):
                    with open(photo_path, 'rb') as photo:
                        # Add caption to first photo only
                        if i == 0:
                            media_group.append(
                                InputMediaPhoto(
                                    media=photo.read(),
                                    caption=message,
                                    parse_mode=ParseMode.HTML
                                )
                            )
                        else:
                            media_group.append(
                                InputMediaPhoto(media=photo.read())
                            )

                # Send all photos as a single media group (album)
                await self.bot.send_media_group(
                    chat_id=self.chat_id,
                    media=media_group
                )

                logger.info(f"Sent listing {listing.get('id')} with {len(photos_to_send)} photos in media group")
            else:
                # Send text-only message
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False
                )
                logger.info(f"Sent listing {listing.get('id')} (text only)")

            return True

        except TelegramError as e:
            logger.error(f"Failed to send listing {listing.get('id')}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending listing {listing.get('id')}: {e}")
            return False

    def _get_listing_photos(self, link: str, photos_dir: Optional[str] = None) -> List[Path]:
        """
        Get list of photo paths for a listing.

        Args:
            link: Listing URL
            photos_dir: Base directory where photos are stored

        Returns:
            List of Path objects for photos, sorted by name
        """
        if not link:
            return []

        photos_base = Path(photos_dir or 'photos')

        # Use same directory structure as photos.py
        import hashlib
        hash_obj = hashlib.md5(link.encode())
        hash_str = hash_obj.hexdigest()

        # Create path: photos/ab/cd/abcd.../
        dir_path = photos_base / hash_str[:2] / hash_str[2:4] / hash_str

        if not dir_path.exists():
            return []

        # Get all image files, sorted by name
        photo_paths = []
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            photo_paths.extend(dir_path.glob(f'*{ext}'))

        return sorted(photo_paths)

    async def send_listings(self, listings: List[Dict], photos_dir: Optional[str] = None) -> int:
        """
        Send multiple listing notifications.

        Args:
            listings: List of listing dictionaries
            photos_dir: Base directory where photos are stored

        Returns:
            Number of successfully sent messages
        """
        if not listings:
            logger.info("No new listings to send")
            return 0

        logger.info(f"Sending {len(listings)} new listing(s) to Telegram")

        sent_count = 0
        for listing in listings:
            success = await self.send_listing(listing, photos_dir)
            if success:
                sent_count += 1

            # Small delay between messages to avoid rate limiting
            await asyncio.sleep(0.5)

        logger.info(f"Successfully sent {sent_count}/{len(listings)} listings")
        return sent_count


def send_listings_sync(bot_token: str, chat_id: str, listings: List[Dict],
                       photos_dir: Optional[str] = None) -> int:
    """
    Synchronous wrapper for sending listings (for use in non-async code).

    Args:
        bot_token: Telegram bot API token
        chat_id: Channel or chat ID
        listings: List of listing dictionaries
        photos_dir: Base directory where photos are stored

    Returns:
        Number of successfully sent messages
    """
    notifier = TelegramNotifier(bot_token, chat_id)
    return asyncio.run(notifier.send_listings(listings, photos_dir))


# Singleton instance
_notifier_instance: Optional[TelegramNotifier] = None


def get_notifier(bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> TelegramNotifier:
    """
    Get singleton Telegram notifier instance.

    Args:
        bot_token: Telegram bot API token (required on first call)
        chat_id: Channel or chat ID (required on first call)

    Returns:
        TelegramNotifier instance
    """
    global _notifier_instance

    if _notifier_instance is None:
        if not bot_token or not chat_id:
            raise ValueError("bot_token and chat_id required for first initialization")
        _notifier_instance = TelegramNotifier(bot_token, chat_id)

    return _notifier_instance
