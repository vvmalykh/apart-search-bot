# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python web scraper for Willhaben.at (Austrian real estate listings). The scraper extracts apartment rental listings from search result pages and exports them to CSV format.

## Running the Script

**Basic usage:**
```bash
python3 parser.py
```

**With custom URL:**
```bash
python3 parser.py --url "https://www.willhaben.at/iad/immobilien/..."
```

**With custom output file:**
```bash
python3 parser.py --out my_listings.csv
```

**Control listings per page:**
```bash
python3 parser.py --rows 100
```

## Dependencies

The script requires:
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- Standard library: `argparse`, `csv`, `json`, `re`, `urllib.parse`

Install with:
```bash
pip3 install requests beautifulsoup4
```

## Architecture

### Data Extraction Strategy

The scraper uses a **multi-layered parsing approach** to maximize data extraction reliability:

1. **JSON-LD parsing** (`extract_from_jsonld`): Attempts to extract structured data from `<script type="application/ld+json">` tags, specifically looking for `ItemList` schemas with listing names and URLs.

2. **HTML card parsing** (`extract_by_card`): Parses individual listing cards from the HTML DOM by:
   - Finding links matching pattern `/iad/immobilien/(?:d/|.*\?adId=)`
   - Traversing up to parent containers (`<article>`, `<li>`, or divs with class patterns like "result", "card", "box", "tile")
   - Extracting data using regex patterns and CSS class heuristics

3. **Fallback mechanisms**: If explicit address/location classes aren't found, uses geographic pattern matching (`guess_address`) to identify location strings containing Austrian region names.

### Key Functions

- `set_rows_param(url, rows)`: URL manipulation to control pagination (default 10,000 results per page)
- `fetch(url)`: HTTP request with browser-like headers to avoid blocking
- `extract_id_from_href(href)`: Extracts listing IDs from URLs using two patterns: query param `?adId=` or path suffix `/123456789`
- `extract_price(text)`: Regex extraction for euro amounts
- `extract_size(text)`: Regex extraction for m² measurements
- `guess_address(lines)`: Heuristic-based address detection using Austrian location keywords
- `parse_list_page(html, base_url)`: Main orchestrator that combines JSON-LD and HTML parsing, deduplicates by link

### Output Format

CSV with columns: `id`, `listing_name`, `price`, `address`, `apart_size`, `link`

### Anti-Scraping Measures

The script uses realistic browser headers (parser.py:23-31) including User-Agent, Accept-Language, and Accept headers to mimic a real browser and reduce likelihood of being blocked.
