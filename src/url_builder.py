"""URL building from environment configuration."""

import os
from typing import Any
from urllib.parse import urlencode

from .config import DEFAULT_BASE_URL, DEFAULT_LISTING_PATH


def build_search_url() -> str:
    """
    Build the Willhaben search URL from environment variables.

    Reads BASE_URL, LISTING_PATH, and various query parameters from .env.
    Multi-value parameters (AREA_IDS, etc.) should be comma-separated.

    Returns:
        Complete URL with all query parameters
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
