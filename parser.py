#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Willhaben.at Apartment Listings Scraper

Scrapes apartment rental listings from Willhaben.at and exports to CSV.
Configuration is loaded from .env file.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# Constants
DEFAULT_OUT = "willhaben_listings.csv"
DEFAULT_ROWS = 10000
DEFAULT_BASE_URL = "https://www.willhaben.at"
DEFAULT_LISTING_PATH = "/iad/immobilien/mietwohnungen/mietwohnung-angebote"
REQUEST_TIMEOUT = 30000  # 30 seconds in milliseconds for Playwright
MIN_ADDRESS_LENGTH = 6
SCROLL_PAUSE_TIME = 2  # seconds to wait between scrolls
MAX_SCROLL_ATTEMPTS = 50  # maximum number of scroll attempts

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CSV_FIELDS = ["id", "listing_name", "price", "address", "apart_size", "link"]

AUSTRIAN_LOCATION_PATTERNS = [
    r"\bWien\b",
    r"\bBezirk\b",
    r"\bNiederösterreich\b",
    r"\bOberösterreich\b",
    r"\bSteiermark\b",
    r"\bBurgenland\b",
    r"\bSalzburg\b",
    r"\bTirol\b",
    r"\bVorarlberg\b",
    r"\bKärnten\b",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def build_url_from_env() -> str:
    """
    Build the Willhaben search URL from environment variables.

    Reads BASE_URL, LISTING_PATH, and various query parameters from environment.
    Multi-value parameters (AREA_IDS, etc.) should be comma-separated.

    Returns:
        Complete URL with all query parameters.
    """
    base_url = os.getenv("BASE_URL", DEFAULT_BASE_URL)
    listing_path = os.getenv("LISTING_PATH", DEFAULT_LISTING_PATH)

    params: dict[str, Any] = {}

    # Single value parameters
    single_params = {
        "rows": "ROWS",
        "sort": "SORT",
        "isNavigation": "IS_NAVIGATION",
        "sfId": "SF_ID",
        "page": "PAGE",
        "PRICE_TO": "PRICE_TO",
        "ESTATE_SIZE/LIVING_AREA_FROM": "ESTATE_SIZE_FROM",
    }

    for param_key, env_key in single_params.items():
        if value := os.getenv(env_key):
            params[param_key] = value

    # Multi-value parameters (comma-separated in .env)
    multi_params = {
        "areaId": "AREA_IDS",
        "NO_OF_ROOMS_BUCKET": "NO_OF_ROOMS_BUCKETS",
        "PROPERTY_TYPE": "PROPERTY_TYPES",
    }

    for param_key, env_key in multi_params.items():
        if value := os.getenv(env_key):
            params[param_key] = [v.strip() for v in value.split(",")]

    query_string = urlencode(params, doseq=True)
    return f"{base_url}{listing_path}?{query_string}"


def set_rows_param(url: str, rows: Optional[int]) -> str:
    """
    Insert or update the 'rows' query parameter in URL.

    If rows is None and URL doesn't have 'rows', sets it to DEFAULT_ROWS.
    If rows is provided, overwrites existing value.

    Args:
        url: URL to modify
        rows: Number of rows to set, or None to keep/set default

    Returns:
        Modified URL with rows parameter
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    if rows is None:
        if "rows" not in query_params:
            query_params["rows"] = [str(DEFAULT_ROWS)]
    else:
        query_params["rows"] = [str(rows)]

    new_query = urlencode(query_params, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def scroll_to_load_all_listings(page: Page) -> None:
    """
    Scroll page to bottom to load all dynamic listings.

    Args:
        page: Playwright Page object

    Raises:
        PlaywrightTimeoutError: If scrolling times out
    """
    last_height = page.evaluate("document.body.scrollHeight")
    scroll_attempts = 0

    logger.info("Starting to scroll page to load all listings...")

    while scroll_attempts < MAX_SCROLL_ATTEMPTS:
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Wait for content to load
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height
        new_height = page.evaluate("document.body.scrollHeight")

        scroll_attempts += 1
        logger.debug(f"Scroll attempt {scroll_attempts}: height {last_height} -> {new_height}")

        # Break if no more content loaded
        if new_height == last_height:
            logger.info(f"Reached bottom of page after {scroll_attempts} scrolls")
            break

        last_height = new_height

    if scroll_attempts >= MAX_SCROLL_ATTEMPTS:
        logger.warning(f"Reached maximum scroll attempts ({MAX_SCROLL_ATTEMPTS})")


def fetch(url: str, headless: bool = True) -> str:
    """
    Fetch HTML content from URL using Playwright with scrolling.

    Uses Playwright to load the page and scrolls to bottom to load
    all dynamically loaded listings.

    Args:
        url: URL to fetch
        headless: Run browser in headless mode (default: True)

    Returns:
        HTML content as string

    Raises:
        PlaywrightTimeoutError: If page load or scrolling times out
        Exception: If any other error occurs
    """
    try:
        logger.info(f"Launching browser to fetch: {url}")

        with sync_playwright() as playwright:
            # Launch browser
            browser = playwright.chromium.launch(headless=headless)

            # Create context with custom user agent
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="de-DE",
                viewport={"width": 1920, "height": 1080}
            )

            # Create page
            page = context.new_page()

            # Navigate to URL
            logger.info("Loading page...")
            page.goto(url, timeout=REQUEST_TIMEOUT, wait_until="networkidle")

            # Wait a bit for initial content
            page.wait_for_timeout(2000)

            # Scroll to load all listings
            scroll_to_load_all_listings(page)

            # Get final HTML
            html = page.content()

            # Cleanup
            context.close()
            browser.close()

            logger.info(f"Successfully fetched page with {len(html)} characters")
            return html

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout while fetching URL {url}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        raise


def normalize_space(text: str) -> str:
    """
    Normalize whitespace in text.

    Replaces multiple whitespace characters with single space and strips.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    return re.sub(r"\s+", " ", text or "").strip()


def extract_id_from_href(href: str) -> Optional[str]:
    """
    Extract listing ID from href.

    Tries two patterns:
    1. Query parameter: ?adId=123456789
    2. Path suffix: /.../123456789

    Args:
        href: URL or path to extract ID from

    Returns:
        Listing ID if found, None otherwise
    """
    # Try query parameter pattern
    match = re.search(r"[?&]adId=(\d+)", href)
    if match:
        return match.group(1)

    # Try path suffix pattern (at least 6 digits)
    match = re.search(r"/(\d{6,})/?$", href)
    if match:
        return match.group(1)

    return None


def extract_price(text: str) -> Optional[str]:
    """
    Extract price from text.

    Finds first occurrence of price with euro symbol.

    Args:
        text: Text to search

    Returns:
        Normalized price string if found, None otherwise
    """
    match = re.search(r"\b[\d.\s]+(?:,\d{2})?\s*€", text)
    if match:
        return normalize_space(match.group(0))
    return None


def extract_size(text: str) -> Optional[str]:
    """
    Extract apartment size from text.

    Finds first occurrence of size with m² unit.

    Args:
        text: Text to search

    Returns:
        Normalized size string (e.g., "50 m²") if found, None otherwise
    """
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*m²", text, flags=re.IGNORECASE)
    if match:
        size_value = match.group(1).replace(',', '.')
        return f"{size_value} m²"
    return None


def guess_address(lines: list[str]) -> Optional[str]:
    """
    Guess address/location from text lines using heuristics.

    First tries to find lines containing Austrian location keywords.
    Falls back to finding informative lines without common listing metadata.

    Args:
        lines: List of text lines to search

    Returns:
        Best guess for address if found, None otherwise
    """
    # Try location patterns first
    for line in lines:
        if any(re.search(pat, line, flags=re.IGNORECASE) for pat in AUSTRIAN_LOCATION_PATTERNS):
            return line

    # Fallback: find informative line without metadata
    metadata_pattern = re.compile(r"€|m²|Zimmer|Gesamtmiete|Kaution|Betriebskosten", re.IGNORECASE)
    for line in lines:
        if len(line) >= MIN_ADDRESS_LENGTH and not metadata_pattern.search(line):
            return line

    return None


def extract_by_card(container: Tag, base_url: str) -> Optional[dict[str, str]]:
    """
    Extract listing data from HTML card container.

    Args:
        container: BeautifulSoup Tag containing listing card
        base_url: Base URL for resolving relative links

    Returns:
        Dictionary with listing fields, or None if extraction fails
    """
    # Find link and title
    anchor = container.find("a", href=True)
    if not anchor:
        return None

    href = anchor["href"]
    link = urljoin(base_url, href)
    listing_name = normalize_space(anchor.get_text(" ", strip=True))

    # Get full card text
    text = normalize_space(container.get_text(" ", strip=True))
    lines = [
        normalize_space(line)
        for line in re.split(r"[•\n\r]+| {2,}", text)
        if normalize_space(line)
    ]

    # Extract structured data
    price = extract_price(text)
    apart_size = extract_size(text)

    # Try to find address from CSS classes first
    address = None
    address_class_patterns = [r"address", r"location", r"region"]
    for pattern in address_class_patterns:
        element = container.find(True, class_=re.compile(pattern, re.IGNORECASE))
        if element:
            address = normalize_space(element.get_text(" ", strip=True))
            break

    # Fallback to heuristic address detection
    if not address:
        address = guess_address(lines)

    # Extract ID from href or data attributes
    ad_id = extract_id_from_href(href)
    if not ad_id:
        data_attrs = ["data-id", "data-adid", "data-item-id", "data-tracking-id"]
        for attr in data_attrs:
            if container.has_attr(attr):
                ad_id = container.get(attr)
                break

    return {
        "id": ad_id or "",
        "listing_name": listing_name,
        "price": price or "",
        "address": address or "",
        "apart_size": apart_size or "",
        "link": link,
    }


def extract_from_jsonld(soup: BeautifulSoup, base_url: str) -> dict[str, dict[str, str]]:
    """
    Extract listing names and URLs from JSON-LD structured data.

    Looks for ItemList schemas in <script type="application/ld+json"> tags.

    Args:
        soup: BeautifulSoup object of the page
        base_url: Base URL for resolving relative links

    Returns:
        Dictionary mapping full URLs to listing data
    """
    items_by_link: dict[str, dict[str, str]] = {}
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse JSON-LD: {e}")
            continue

        # Handle both single objects and arrays
        payloads = data if isinstance(data, list) else [data]

        for payload in payloads:
            if not isinstance(payload, dict):
                continue

            if payload.get("@type") == "ItemList" and "itemListElement" in payload:
                for list_item in payload["itemListElement"]:
                    if not isinstance(list_item, dict):
                        continue

                    # Extract URL and name from different schema structures
                    url = list_item.get("url")
                    name = list_item.get("name")

                    # Check nested item object
                    if item_obj := list_item.get("item"):
                        if isinstance(item_obj, dict):
                            url = url or item_obj.get("url") or item_obj.get("@id")
                            name = name or item_obj.get("name")

                    if url:
                        full_url = urljoin(base_url, url)
                        items_by_link[full_url] = {
                            "listing_name": normalize_space(name or "")
                        }

    return items_by_link


def parse_list_page(html: str, base_url: str = DEFAULT_BASE_URL) -> list[dict[str, str]]:
    """
    Parse Willhaben listing page HTML.

    Uses multi-layered approach:
    1. Extract structured data from JSON-LD
    2. Find listing cards via anchor links
    3. Extract data from each card
    4. Merge with JSON-LD data and deduplicate

    Args:
        html: HTML content of the page
        base_url: Base URL for resolving relative links

    Returns:
        List of listing dictionaries
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract titles from JSON-LD structured data
    jsonld_titles = extract_from_jsonld(soup, base_url)
    logger.debug(f"Found {len(jsonld_titles)} items in JSON-LD")

    # Find all listing links
    listing_link_pattern = re.compile(r"^/iad/immobilien/(?:d/|.*\?adId=)")
    anchors = soup.find_all("a", href=listing_link_pattern)
    logger.debug(f"Found {len(anchors)} listing anchors")

    seen_links: set[str] = set()
    results: list[dict[str, str]] = []

    for anchor in anchors:
        link = urljoin(base_url, anchor.get("href", ""))
        if link in seen_links:
            continue
        seen_links.add(link)

        # Find card container
        container = (
            anchor.find_parent("article")
            or anchor.find_parent("li")
            or anchor.find_parent("div", class_=re.compile(r"(result|card|box|tile)", re.IGNORECASE))
            or anchor.parent
        )

        item = extract_by_card(container, base_url)
        if not item:
            continue

        # Enhance with JSON-LD title if available and current title is empty
        if not item.get("listing_name") and link in jsonld_titles:
            item["listing_name"] = jsonld_titles[link].get("listing_name", "")

        results.append(item)

    # Filter out invalid items (must have link and either ID or title)
    filtered = [
        item for item in results
        if item.get("link") and (item.get("id") or item.get("listing_name"))
    ]

    # Deduplicate by link
    unique_items: dict[str, dict[str, str]] = {}
    for item in filtered:
        unique_items[item["link"]] = item

    logger.info(f"Parsed {len(unique_items)} unique listings")
    return list(unique_items.values())


def write_csv(rows: list[dict[str, str]], out_path: str) -> None:
    """
    Write listing data to CSV file.

    Args:
        rows: List of listing dictionaries
        out_path: Path to output CSV file

    Raises:
        IOError: If file cannot be written
    """
    try:
        with open(out_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
        logger.info(f"Wrote {len(rows)} listings to {out_path}")
    except IOError as e:
        logger.error(f"Failed to write CSV file {out_path}: {e}")
        raise


def main() -> int:
    """
    Main entry point for the scraper.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Load environment variables
    load_dotenv()

    # Build default URL from environment
    default_url = build_url_from_env()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Parse Willhaben listing page into CSV.",
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
        help="Run browser in non-headless mode (visible browser)"
    )
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Build URL and fetch
        url = set_rows_param(args.url, args.rows)
        logger.info(f"Fetching listings from: {url}")

        html = fetch(url, headless=not args.no_headless)

        # Parse and extract listings
        items = parse_list_page(html)

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
