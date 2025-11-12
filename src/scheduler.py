"""
Scheduler module for periodic apartment listing scraping and notifications.

This module orchestrates:
- Periodic scraping runs
- Detecting new listings
- Sending Telegram notifications
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src import (
    fetch,
    set_rows_param,
    parse_listings,
    get_non_promoted_listing_links,
    build_search_url,
    get_logger,
    get_database,
    download_photos_for_listings,
)

logger = logging.getLogger(__name__)
action_logger = get_logger()


class ScraperScheduler:
    """Handles periodic scraping and notifications."""

    def __init__(
        self,
        interval_minutes: int,
        url: Optional[str] = None,
        rows: Optional[int] = None,
        headless: bool = True,
        download_photos: bool = True,
        on_new_listings: Optional[Callable] = None,
    ):
        """
        Initialize scheduler.

        Args:
            interval_minutes: How often to run scraper (in minutes)
            url: Search URL (default: built from .env)
            rows: Number of results per page (default: from .env)
            headless: Run browser in headless mode
            download_photos: Whether to download photos for new listings
            on_new_listings: Callback function(new_listings) to call when new listings found
        """
        self.interval_minutes = interval_minutes
        self.url = url or build_search_url()
        self.rows = rows
        self.headless = headless
        self.download_photos = download_photos
        self.on_new_listings = on_new_listings
        self.running = False

        logger.info(f"Scheduler initialized: interval={interval_minutes}min, url={self.url}")

    def run_once(self) -> int:
        """
        Run scraper once and notify if new listings found.

        Returns:
            Number of new listings found
        """
        try:
            db = get_database()

            # Track time before scraping to detect new listings
            before_scrape = datetime.now()

            # Start database run
            run_id = db.start_run()
            action_logger.parsing_started(self.url)

            # Build URL
            url = set_rows_param(self.url, self.rows)
            logger.info(f"Fetching listings from: {url}")

            # Create smart scrolling callback
            def check_should_continue_scrolling(html: str) -> bool:
                """Check if we should continue scrolling based on seen listings."""
                listing_links = get_non_promoted_listing_links(html)

                if not listing_links:
                    return True

                # Check each listing from top to bottom
                for link in listing_links:
                    if db.listing_exists(link):
                        logger.info("Smart scrolling: Reached already-seen listing, stopping")
                        return False

                return True

            # Fetch with smart scrolling
            html = fetch(
                url,
                headless=self.headless,
                should_continue_scrolling=check_should_continue_scrolling
            )

            # Parse listings
            items = parse_listings(html)

            if not items:
                logger.warning("No listings found")
                db.finish_run(
                    run_id=run_id,
                    listings_found=0,
                    new_listings=0,
                    updated_listings=0,
                    status="success"
                )
                return 0

            # Save to database
            new_count, updated_count = db.save_listings(items)

            db.finish_run(
                run_id=run_id,
                listings_found=len(items),
                new_listings=new_count,
                updated_listings=updated_count,
                status="success"
            )

            action_logger.records_added(len(items))
            logger.info(f"Saved {len(items)} listings: {new_count} new, {updated_count} updated")

            # Get new listings and process them
            if new_count > 0:
                # Get new listings from this run
                cutoff_time = before_scrape - timedelta(seconds=10)
                new_listings = db.get_new_listings_since(cutoff_time)

                logger.info(f"Found {len(new_listings)} new listings")

                # Download photos if enabled
                if self.download_photos and new_listings:
                    logger.info(f"Downloading photos for {len(new_listings)} new listings...")
                    stats = download_photos_for_listings(new_listings, headless=self.headless)
                    logger.info(
                        f"Photo download complete: {stats['photos_downloaded']} downloaded, "
                        f"{stats['skipped']} skipped, {stats['errors']} errors"
                    )

                # Call notification callback
                if self.on_new_listings and new_listings:
                    try:
                        self.on_new_listings(new_listings)
                    except Exception as e:
                        logger.error(f"Error in notification callback: {e}", exc_info=True)

            return new_count

        except PlaywrightTimeoutError as e:
            logger.error(f"Browser timeout: {e}")
            action_logger.error("Browser timeout", e)
            return 0
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            action_logger.error("Scraping error", e)
            return 0

    def run_forever(self):
        """Run scheduler continuously at specified interval."""
        self.running = True
        logger.info(f"Starting scheduler: running every {self.interval_minutes} minutes")
        action_logger.info(f"Scheduler started: interval={self.interval_minutes}min")

        run_count = 0

        while self.running:
            run_count += 1
            logger.info(f"=== Scraper run #{run_count} starting ===")

            try:
                new_count = self.run_once()
                logger.info(f"=== Scraper run #{run_count} complete: {new_count} new listings ===")
            except Exception as e:
                logger.error(f"Unexpected error in run #{run_count}: {e}", exc_info=True)

            # Wait for next interval
            if self.running:
                sleep_seconds = self.interval_minutes * 60
                logger.info(f"Sleeping for {self.interval_minutes} minutes until next run...")
                time.sleep(sleep_seconds)

    def stop(self):
        """Stop the scheduler gracefully."""
        logger.info("Stopping scheduler...")
        self.running = False
