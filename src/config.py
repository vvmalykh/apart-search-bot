"""Configuration and constants for the Willhaben scraper."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Output defaults
DEFAULT_OUT = "willhaben_listings.csv"
DEFAULT_BASE_URL = "https://www.willhaben.at"
DEFAULT_LISTING_PATH = "/iad/immobilien/mietwohnungen/mietwohnung-angebote"
DEFAULT_ROWS = 10000

# CSV export fields
CSV_FIELDS = ["id", "listing_name", "price", "address", "apart_size", "link"]

# Browser automation settings
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30000"))
INITIAL_CONTENT_WAIT = int(os.getenv("INITIAL_CONTENT_WAIT", "2000"))
SCROLL_WAIT_SHORT = int(os.getenv("SCROLL_WAIT_SHORT", "300"))
SCROLL_WAIT_LONG = int(os.getenv("SCROLL_WAIT_LONG", "1500"))
SCROLL_LONG_WAIT_FREQUENCY = int(os.getenv("SCROLL_LONG_WAIT_FREQUENCY", "10"))
SCROLL_LOG_FREQUENCY = int(os.getenv("SCROLL_LOG_FREQUENCY", "5"))
SCROLL_WAIT_FINAL = int(os.getenv("SCROLL_WAIT_FINAL", "2000"))
SCROLL_STALE_THRESHOLD = int(os.getenv("SCROLL_STALE_THRESHOLD", "5"))
MAX_SCROLL_ATTEMPTS = int(os.getenv("MAX_SCROLL_ATTEMPTS", "100"))

# Parsing settings
MIN_ADDRESS_LENGTH = int(os.getenv("MIN_ADDRESS_LENGTH", "6"))

# Browser headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Austrian location patterns for address detection
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
