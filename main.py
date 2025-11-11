#!/usr/bin/env python3
"""
Willhaben.at Apartment Listings Scraper

Main entry point for the scraper CLI.
"""

import argparse
import logging
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src import (
    DEFAULT_OUT,
    fetch,
    set_rows_param,
    parse_listings,
    write_csv,
    build_search_url,
    get_logger,
    get_database,
    HAS_DATABASE,
)

# Configure standard logging for console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Get action logger for detailed action tracking
action_logger = get_logger()


def main() -> int:
    """
    Main entry point for the scraper.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Build default URL from environment
    default_url = build_search_url()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Scrape Willhaben apartment listings and export to CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default=default_url,
        help="Willhaben search URL (default: built from .env)"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Number of results per page (overrides .env ROWS)"
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output CSV file path (default: {DEFAULT_OUT})"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (for debugging)"
    )
    parser.add_argument(
        "--use-csv",
        action="store_true",
        help="Save to CSV instead of database (legacy mode)"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database operations (useful for testing)"
    )
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Determine storage mode
        use_database = not args.use_csv and not args.no_db and HAS_DATABASE

        if not HAS_DATABASE and not args.use_csv:
            logger.warning("Database module not available (psycopg2 not installed). Using CSV mode.")

        # Log app initialization
        storage_mode = "database" if use_database else "CSV"
        action_logger.app_init(f"Version: MVP, Storage: {storage_mode}, Output: {args.out}")

        # Build URL and fetch
        url = set_rows_param(args.url, args.rows)
        logger.info(f"Fetching listings from: {url}")
        action_logger.parsing_started(url)

        html = fetch(url, headless=not args.no_headless)

        # Parse and extract listings
        items = parse_listings(html)

        if not items:
            logger.warning("No listings found")
            action_logger.warning("No listings found - parsing completed with 0 results")
            return 1

        # Save to database or CSV
        if use_database:
            try:
                db = get_database()
                run_id = db.start_run()

                new_count, updated_count = db.save_listings(items)

                db.finish_run(
                    run_id=run_id,
                    listings_found=len(items),
                    new_listings=new_count,
                    updated_listings=updated_count,
                    status="success"
                )

                action_logger.records_added(len(items))
                print(f"✓ Saved {len(items)} listings to database: {new_count} new, {updated_count} updated")

                # Also save to CSV as backup if --out is specified
                if args.out != DEFAULT_OUT:
                    write_csv(items, args.out)
                    logger.info(f"Also saved to CSV: {args.out}")

                db.close_all()

            except Exception as e:
                logger.error(f"Database error: {e}. Falling back to CSV.")
                action_logger.error("Database error, falling back to CSV", e)
                write_csv(items, args.out)
                action_logger.records_added(len(items))
                print(f"✓ Saved {len(items)} listings to CSV (database failed) → {args.out}")
        else:
            # CSV mode
            write_csv(items, args.out)
            action_logger.records_added(len(items))
            print(f"✓ Parsed {len(items)} listings → {args.out}")

        return 0

    except PlaywrightTimeoutError as e:
        logger.error(f"Browser timeout: {e}")
        action_logger.error("Browser timeout", e)
        return 1
    except IOError as e:
        logger.error(f"File I/O error: {e}")
        action_logger.error("File I/O error", e)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        action_logger.error("Unexpected error", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
