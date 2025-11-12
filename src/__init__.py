"""Willhaben.at Apartment Listings Scraper."""

from .config import DEFAULT_OUT, DEFAULT_BASE_URL
from .scraper import fetch, set_rows_param
from .parser import parse_listings, get_non_promoted_listing_links
from .exporter import write_csv
from .url_builder import build_search_url
from .logger import get_logger, ActionLogger
from .photos import download_listing_photos, download_photos_for_listings

# Optional database import (requires psycopg2)
try:
    from .database import get_database, Database
    HAS_DATABASE = True
except ImportError:
    get_database = None
    Database = None
    HAS_DATABASE = False

__all__ = [
    "DEFAULT_OUT",
    "DEFAULT_BASE_URL",
    "fetch",
    "set_rows_param",
    "parse_listings",
    "get_non_promoted_listing_links",
    "write_csv",
    "build_search_url",
    "get_logger",
    "ActionLogger",
    "get_database",
    "Database",
    "HAS_DATABASE",
    "download_listing_photos",
    "download_photos_for_listings",
]
