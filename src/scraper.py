"""Browser automation and web scraping using Playwright."""

import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

from .config import (
    HEADERS,
    REQUEST_TIMEOUT,
    INITIAL_CONTENT_WAIT,
    SCROLL_WAIT_SHORT,
    SCROLL_WAIT_LONG,
    SCROLL_LONG_WAIT_FREQUENCY,
    SCROLL_LOG_FREQUENCY,
    SCROLL_WAIT_FINAL,
    SCROLL_STALE_THRESHOLD,
    MAX_SCROLL_ATTEMPTS,
    DEFAULT_ROWS,
)
from .logger import get_logger

logger = logging.getLogger(__name__)
action_logger = get_logger()


def set_rows_param(url: str, rows: int | None) -> str:
    """
    Insert or update the 'rows' query parameter in URL.

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


def scroll_to_load_all_listings(page: Page, should_continue_callback=None) -> None:
    """
    Scroll page to bottom to load all dynamically-loaded listings.

    Optionally accepts a callback to determine if scrolling should continue.
    The callback receives current HTML and returns True to continue, False to stop.

    Args:
        page: Playwright Page object
        should_continue_callback: Optional callable(html: str) -> bool
                                 Returns True to continue scrolling, False to stop

    Raises:
        PlaywrightTimeoutError: If scrolling times out
    """
    logger.info("Starting to scroll page to load all listings...")

    last_height = page.evaluate("document.body.scrollHeight")
    scroll_attempts = 0
    no_change_count = 0
    stopped_by_callback = False

    while scroll_attempts < MAX_SCROLL_ATTEMPTS:
        # Scroll down by one viewport height
        page.evaluate("window.scrollBy(0, window.innerHeight)")

        # Wait for dynamic content - longer wait every N scrolls
        if scroll_attempts % SCROLL_LONG_WAIT_FREQUENCY == 0:
            page.wait_for_timeout(SCROLL_WAIT_LONG)
        else:
            page.wait_for_timeout(SCROLL_WAIT_SHORT)

        # Get new scroll height
        new_height = page.evaluate("document.body.scrollHeight")
        scroll_attempts += 1

        # Check callback if provided (check every few scrolls to avoid overhead)
        if should_continue_callback and scroll_attempts % 3 == 0:
            current_html = page.content()
            should_continue = should_continue_callback(current_html)
            if not should_continue:
                logger.info(f"Callback requested stop after {scroll_attempts} scrolls (all new listings loaded)")
                stopped_by_callback = True
                break

        # Check if page height changed
        if new_height > last_height:
            if scroll_attempts % SCROLL_LOG_FREQUENCY == 0:
                logger.debug(f"Scroll {scroll_attempts}: Page height: {new_height}px")
            last_height = new_height
            no_change_count = 0
        else:
            no_change_count += 1

            # If height hasn't changed for N scrolls, try one final big scroll
            if no_change_count >= SCROLL_STALE_THRESHOLD:
                logger.debug(f"No change for {no_change_count} scrolls, doing final scroll...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(SCROLL_WAIT_FINAL)

                # Check one more time
                final_height = page.evaluate("document.body.scrollHeight")
                if final_height == last_height:
                    logger.info(f"Reached bottom after {scroll_attempts} scrolls. Final height: {final_height}px")
                    break
                else:
                    logger.debug(f"Page expanded to {final_height}px, continuing...")
                    last_height = final_height
                    no_change_count = 0

    # Count total listings found
    listing_count = page.evaluate('document.querySelectorAll(\'a[href*="/iad/immobilien/d/"]\').length')
    logger.info(f"Total listing links found on page: {listing_count}")

    # Log scrolling completion
    action_logger.scrolling_finished(scroll_attempts)

    if stopped_by_callback:
        logger.info("Smart scrolling: stopped early (encountered seen listings)")
    elif scroll_attempts >= MAX_SCROLL_ATTEMPTS:
        logger.warning(f"Reached maximum scroll attempts ({MAX_SCROLL_ATTEMPTS})")


def fetch(url: str, headless: bool = True, should_continue_scrolling=None) -> str:
    """
    Fetch HTML content from URL using Playwright with scrolling.

    Args:
        url: URL to fetch
        headless: Run browser in headless mode (default: True)
        should_continue_scrolling: Optional callable(html: str) -> bool
                                  Callback to determine if scrolling should continue

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
            action_logger.open_site(url)
            page.goto(url, timeout=REQUEST_TIMEOUT, wait_until="networkidle")

            # Wait for initial content to load
            page.wait_for_timeout(INITIAL_CONTENT_WAIT)
            action_logger.site_loaded(INITIAL_CONTENT_WAIT)

            # Scroll to load all listings (with optional smart stop)
            scroll_to_load_all_listings(page, should_continue_callback=should_continue_scrolling)

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
