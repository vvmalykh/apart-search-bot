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
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Build URL and fetch
        url = set_rows_param(args.url, args.rows)
        logger.info(f"Fetching listings from: {url}")

        html = fetch(url, headless=not args.no_headless)

        # Parse and extract listings
        items = parse_listings(html)

        if not items:
            logger.warning("No listings found")
            return 1

        # Write to CSV
        write_csv(items, args.out)
        print(f"✓ Parsed {len(items)} listings → {args.out}")
        return 0

    except PlaywrightTimeoutError as e:
        logger.error(f"Browser timeout: {e}")
        return 1
    except IOError as e:
        logger.error(f"File I/O error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
