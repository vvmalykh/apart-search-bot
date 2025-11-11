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

The codebase is organized into clean, focused modules for maintainability and AI-assisted development:

```
src/
├── config.py       # All constants and environment configuration
├── url_builder.py  # URL construction from .env parameters
├── scraper.py      # Browser automation with Playwright
├── parser.py       # HTML parsing and data extraction
├── exporter.py     # CSV export functionality
└── logger.py       # Action logging and tracking

main.py             # CLI entry point
parser.py           # Backward compatibility shim
```

### Module Responsibilities

**`src/config.py`**: Central configuration
- All constants (URLs, timeouts, CSV fields)
- Environment variable loading
- Browser headers and patterns

**`src/url_builder.py`**: URL construction
- `build_search_url()`: Builds Willhaben URL from .env parameters

**`src/scraper.py`**: Browser automation
- `fetch(url, headless)`: Launches Playwright, loads page, returns HTML
- `scroll_to_load_all_listings(page)`: Scrolls to load all dynamic content
- `set_rows_param(url, rows)`: URL manipulation for pagination

**`src/parser.py`**: Data extraction
- `parse_listings(html, base_url)`: Main parsing orchestrator
- `extract_from_jsonld()`: Extracts data from JSON-LD structured data
- `extract_by_card()`: Parses individual listing cards
- `extract_price()`, `extract_size()`, `extract_address_from_text()`: Regex extractors
- `clean_listing_name()`: Removes metadata from listing titles
- `guess_address()`: Heuristic-based address detection

**`src/exporter.py`**: CSV export
- `write_csv(rows, out_path)`: Writes listings to CSV file

**`src/logger.py`**: Action logging and tracking
- `get_logger()`: Get singleton logger instance
- Logs all major actions with timestamps (24h format)
- Human-friendly format stored in `output/scraper.log`
- Append mode (preserves previous logs)
- Pre-built methods for current and future actions
- See `LOGGING.md` for complete documentation

### Dynamic Content Loading

The scraper uses **Playwright** for browser automation:
- Launches headless Chromium browser
- Navigates to search URL and waits for networkidle
- **Scrolls to bottom** repeatedly to load all dynamically-loaded listings
- Stops when no new content is loaded or max scroll attempts reached
- Extracts final HTML after all content is loaded

### Data Extraction Strategy

Multi-layered parsing approach for maximum reliability:

1. **JSON-LD parsing**: Extracts structured data from `<script type="application/ld+json">` tags
2. **HTML card parsing**: Parses listing cards by finding links and traversing to parent containers
3. **Fallback mechanisms**: Uses geographic pattern matching to identify addresses

### Output Format

CSV with columns: `id`, `listing_name`, `price`, `address`, `apart_size`, `link`

### Anti-Scraping Measures

Uses realistic browser headers (src/config.py) including User-Agent, Accept-Language, and Accept headers to mimic a real browser.
