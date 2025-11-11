"""HTML parsing and data extraction from Willhaben listings."""

import json
import logging
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .config import (
    DEFAULT_BASE_URL,
    MIN_ADDRESS_LENGTH,
    AUSTRIAN_LOCATION_PATTERNS,
)

logger = logging.getLogger(__name__)


def normalize_space(text: str) -> str:
    """
    Normalize whitespace in text.

    Args:
        text: Text to normalize

    Returns:
        Normalized text with single spaces
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

    Args:
        text: Text to search

    Returns:
        Normalized price string if found, None otherwise
    """
    # Try Austrian/German format: € 1.000 or € 1.000,50
    match = re.search(r"€\s*((?:[\d.\s]+?)(?:,\d{2})?)(?=\s+\d{4}(?:\s|$)|[^\d,.\s]|$)", text)
    if match:
        price_num = normalize_space(match.group(1))
        return f"€ {price_num}"

    # Fallback: alternative format 1000€
    match = re.search(r"\b([\d.\s]+(?:,\d{2})?)\s*€", text)
    if match:
        return f"{normalize_space(match.group(1))} €"

    return None


def extract_size(text: str) -> Optional[str]:
    """
    Extract apartment size from text.

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


def extract_address_from_text(text: str) -> Optional[str]:
    """
    Extract address from text using pattern matching.

    Looks for Austrian address format: postal code + city/district.

    Args:
        text: Text to search

    Returns:
        Extracted address if found, None otherwise
    """
    # Pattern for Austrian addresses: 4-digit postal code followed by location
    match = re.search(r"\b\d{4}\s+[A-ZÄÖÜa-zäöüß][^€]+?(?:Bezirk|[A-ZÄÖÜ][a-zäöüß]+)(?:,\s*[^€\d]+)?", text)
    if match:
        address = match.group(0)
        # Clean up: remove trailing metadata
        address = re.sub(r'\s*\d+\s*m².*$', '', address)
        address = re.sub(r'\s*€.*$', '', address)
        address = re.sub(r'\s*\d+\s*Zimmer.*$', '', address)
        return normalize_space(address)

    return None


def guess_address(lines: list[str]) -> Optional[str]:
    """
    Guess address/location from text lines using heuristics.

    Args:
        lines: List of text lines to search

    Returns:
        Best guess for address if found, None otherwise
    """
    # Try location patterns first
    for line in lines:
        if any(re.search(pat, line, flags=re.IGNORECASE) for pat in AUSTRIAN_LOCATION_PATTERNS):
            clean_addr = extract_address_from_text(line)
            if clean_addr:
                return clean_addr
            return line

    # Fallback: find informative line without metadata
    metadata_pattern = re.compile(r"€|m²|Zimmer|Gesamtmiete|Kaution|Betriebskosten", re.IGNORECASE)
    for line in lines:
        if len(line) >= MIN_ADDRESS_LENGTH and not metadata_pattern.search(line):
            return line

    return None


def clean_listing_name(name: str) -> str:
    """
    Clean listing name by removing metadata.

    Args:
        name: Raw listing name

    Returns:
        Cleaned listing name
    """
    # Remove Austrian postal code + address
    name = re.sub(r'\s+\d{4}\s+Wien,\s+\d+\.\s+Bezirk[^€]*', '', name)

    # Remove size with m²
    name = re.sub(r'\s+\d+(?:[.,]\d+)?\s*m²', '', name)

    # Remove price
    name = re.sub(r'\s*€\s*[\d.\s,]+', '', name)

    # Remove isolated room count
    name = re.sub(r'\s+\d+\s+Zimmer(?!\w)', '', name)

    # Remove trailing property features
    name = re.sub(r'\s+(Balkon|Loggia|Terrasse|Garten)\s*$', '', name, flags=re.IGNORECASE)

    # Remove company names
    name = re.sub(r'\s+(?:Blueground|Hubner|EHL|OPTIN|KALANDRA|Mayrhofer|MP|EDEX|Mittelsmann|Zirkel)\s+(?:Austria\s+)?(?:GmbH|OG|KG|AG|Immobilien)?\s*$', '', name, flags=re.IGNORECASE)

    # Remove standalone trailing company suffixes
    name = re.sub(r'\s+(?:GmbH|OG|KG|AG|Immobilien|Privat)\s*$', '', name, flags=re.IGNORECASE)

    # Remove trailing street names
    name = re.sub(r',\s+[A-ZÄÖÜ][a-zäöüß]+(?:straße|gasse|platz|weg)\s*$', '', name, flags=re.IGNORECASE)

    # Clean up multiple spaces
    name = normalize_space(name)

    # Remove trailing/leading commas
    name = re.sub(r'^[,\s]+|[,\s]+$', '', name)

    return name


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
    raw_listing_name = normalize_space(anchor.get_text(" ", strip=True))

    # Get full card text
    text = normalize_space(container.get_text(" ", strip=True))

    # Clean listing name
    listing_name = clean_listing_name(raw_listing_name)
    lines = [
        normalize_space(line)
        for line in re.split(r"[•\n\r]+| {2,}", text)
        if normalize_space(line)
    ]

    # Extract structured data
    price = extract_price(text)
    apart_size = extract_size(text)

    # Try to extract address from full card text first
    address = extract_address_from_text(text)

    # If not found, try CSS classes
    if not address:
        address_class_patterns = [r"address", r"location", r"region"]
        for pattern in address_class_patterns:
            element = container.find(True, class_=re.compile(pattern, re.IGNORECASE))
            if element:
                elem_text = normalize_space(element.get_text(" ", strip=True))
                address = extract_address_from_text(elem_text) or elem_text
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

                    # Extract URL and name
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


def parse_listings(html: str, base_url: str = DEFAULT_BASE_URL) -> list[dict[str, str]]:
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
    listing_link_pattern = re.compile(r"/iad/immobilien/")
    anchors = soup.find_all("a", href=listing_link_pattern)
    logger.debug(f"Found {len(anchors)} listing anchors")

    seen_links: set[str] = set()
    results: list[dict[str, str]] = []

    for anchor in anchors:
        href = anchor.get("href", "")
        link = urljoin(base_url, href)

        # Skip if already seen
        if link in seen_links:
            continue

        # Filter: Only process actual listing detail pages
        if "/d/" not in href and "?adId=" not in href:
            continue

        seen_links.add(link)

        # Find card container
        container = (
            anchor.find_parent("article")
            or anchor.find_parent("li")
            or anchor.find_parent("div", class_=re.compile(r"(result|card|box|tile)", re.IGNORECASE))
            or anchor.parent
        )

        # Skip promoted/featured listings (TOP-ANZEIGEN)
        if container:
            container_text = container.get_text(" ", strip=True)
            container_classes = " ".join(container.get("class", [])).lower()
            container_html = str(container)[:500].lower()  # Check raw HTML too

            # Check CSS classes for promoted indicators
            promoted_class_keywords = [
                "top-anzeige", "topanzeige", "top_anzeige",
                "promoted", "featured", "sponsored", "premium",
                "highlight", "vip", "boost"
            ]
            if any(keyword in container_classes for keyword in promoted_class_keywords):
                logger.info(f"Skipping promoted listing (class): {link}")
                continue

            # Check visible text for TOP-ANZEIGEN markers
            if re.search(r"TOP[- ]ANZEIGEN?", container_text, re.IGNORECASE):
                logger.info(f"Skipping TOP-ANZEIGEN listing (text): {link}")
                continue

            # Check for data attributes that might indicate promoted status
            if container.get("data-promoted") or container.get("data-featured"):
                logger.info(f"Skipping promoted listing (data-attr): {link}")
                continue

            # Check for any parent with promoted classes
            parent = container.parent
            for _ in range(3):  # Check up to 3 levels up
                if parent and parent.name:
                    parent_classes = " ".join(parent.get("class", [])).lower()
                    if any(keyword in parent_classes for keyword in promoted_class_keywords):
                        logger.info(f"Skipping promoted listing (parent class): {link}")
                        break
                    parent = parent.parent
            else:
                # No promoted parent found, continue processing
                pass

            # If we broke out of the loop, skip this listing
            if parent and parent.name:
                parent_classes = " ".join(parent.get("class", [])).lower()
                if any(keyword in parent_classes for keyword in promoted_class_keywords):
                    continue

        item = extract_by_card(container, base_url)
        if not item:
            continue

        # Enhance with JSON-LD title if available
        if not item.get("listing_name") and link in jsonld_titles:
            item["listing_name"] = jsonld_titles[link].get("listing_name", "")

        results.append(item)

    # Filter out invalid items
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
