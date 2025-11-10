# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python web scraper for Willhaben.at (Austrian real estate listings). The scraper uses Playwright to load dynamic content, automatically scrolls to load all listings, and exports them to CSV format. Fully Dockerized for easy deployment.

## Configuration

The script uses a `.env` file for configuration. Create this file with the following variables:

```
BASE_URL=https://www.willhaben.at
LISTING_PATH=/iad/immobilien/mietwohnungen/mietwohnung-angebote
ROWS=10000
SORT=1
IS_NAVIGATION=true
SF_ID=81997263-28bb-4349-977e-ca13391b025e
AREA_IDS=117225,117239,117240,117241
NO_OF_ROOMS_BUCKETS=2X2,3X3,4X4,5X5
PROPERTY_TYPES=110,102,3
PAGE=1
PRICE_TO=2000
ESTATE_SIZE_FROM=45
```

**Key configuration variables:**
- `BASE_URL` - Willhaben base URL
- `LISTING_PATH` - Path to listings page
- `ROWS` - Number of results per page (default: 10000)
- `AREA_IDS` - Comma-separated area IDs (Vienna districts)
- `NO_OF_ROOMS_BUCKETS` - Room count filters (2X2=2 rooms, etc.)
- `PROPERTY_TYPES` - Property type IDs
- `PRICE_TO` - Maximum price filter
- `ESTATE_SIZE_FROM` - Minimum size in m²

## Running the Script

### Docker (Recommended)

**Build and run:**
```bash
make build
make run
```

**Other commands:**
- `make run-verbose` - Run with detailed logging
- `make shell` - Open bash shell in container
- `make clean` - Remove image and output files
- `make rebuild` - Clean rebuild

Output saved to: `./output/willhaben_listings.csv`

### Local Python

**Basic usage:**
```bash
python3 parser.py
```

**With options:**
```bash
python3 parser.py --verbose              # Detailed logs
python3 parser.py --no-headless          # Show browser
python3 parser.py --rows 100             # Override ROWS
python3 parser.py --out custom.csv       # Custom output
```

## Dependencies

The script requires:
- `playwright` - Browser automation and dynamic content loading
- `beautifulsoup4` - HTML parsing
- `python-dotenv` - Environment variable loading
- Standard library: `argparse`, `csv`, `json`, `logging`, `os`, `re`, `sys`, `time`, `urllib.parse`

Install with:
```bash
pip3 install -r requirements.txt
playwright install chromium
```

Or use Docker (includes everything):
```bash
make build
```

## Architecture

### Dynamic Content Loading

The scraper uses **Playwright** for browser automation:
- Launches headless Chromium browser
- Navigates to search URL and waits for networkidle
- **Scrolls to bottom** repeatedly to load all dynamically-loaded listings
- Stops when no new content is loaded or max scroll attempts reached
- Extracts final HTML after all content is loaded

### Data Extraction Strategy

The scraper uses a **multi-layered parsing approach** to maximize data extraction reliability:

1. **JSON-LD parsing** (`extract_from_jsonld`): Attempts to extract structured data from `<script type="application/ld+json">` tags, specifically looking for `ItemList` schemas with listing names and URLs.

2. **HTML card parsing** (`extract_by_card`): Parses individual listing cards from the HTML DOM by:
   - Finding links matching pattern `/iad/immobilien/(?:d/|.*\?adId=)`
   - Traversing up to parent containers (`<article>`, `<li>`, or divs with class patterns like "result", "card", "box", "tile")
   - Extracting data using regex patterns and CSS class heuristics

3. **Fallback mechanisms**: If explicit address/location classes aren't found, uses geographic pattern matching (`guess_address`) to identify location strings containing Austrian region names.

### Key Functions

- `build_url_from_env()`: Constructs search URL from environment variables in `.env` file, handling both single and multi-value query parameters
- `set_rows_param(url, rows)`: URL manipulation to control pagination (default from .env ROWS variable)
- `scroll_to_load_all_listings(page)`: Scrolls Playwright page to bottom repeatedly until all content loaded
- `fetch(url, headless)`: Launches Playwright browser, loads URL, scrolls to load all content, returns HTML
- `extract_id_from_href(href)`: Extracts listing IDs from URLs using two patterns: query param `?adId=` or path suffix `/123456789`
- `extract_price(text)`: Regex extraction for euro amounts
- `extract_size(text)`: Regex extraction for m² measurements
- `guess_address(lines)`: Heuristic-based address detection using Austrian location keywords
- `parse_list_page(html, base_url)`: Main orchestrator that combines JSON-LD and HTML parsing, deduplicates by link

### Output Format

CSV with columns: `id`, `listing_name`, `price`, `address`, `apart_size`, `link`

### Anti-Scraping Measures

The script uses realistic browser headers (parser.py:23-31) including User-Agent, Accept-Language, and Accept headers to mimic a real browser and reduce likelihood of being blocked.
