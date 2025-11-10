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

**Disable Google Sheets upload:**
```bash
python3 parser.py --no-sheets
```

## Google Sheets Integration

The script automatically uploads results to Google Sheets if configured.

### Setup Steps

1. **Create a Google Cloud Project and Service Account:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Sheets API and Google Drive API
   - Create a Service Account at IAM & Admin > Service Accounts
   - Download the JSON credentials file and save as `credentials.json` in the project root

2. **Configure Environment Variables:**
   - Copy the Google Sheets URL from your browser
   - Add it to `.env` file:
   ```
   GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
   ```

3. **Share Your Google Sheet:**
   - Open the `credentials.json` file and find the `client_email` field
   - Share your Google Sheet with this email address (Editor permission)

4. **Run the Script:**
   - The script will automatically upload to Google Sheets after saving to CSV
   - To skip Google Sheets upload, use `--no-sheets` flag

## Dependencies

The script requires:
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `python-dotenv` - Environment variable management
- `gspread` - Google Sheets API
- `google-auth` - Google authentication
- Standard library: `argparse`, `csv`, `json`, `re`, `urllib.parse`, `os`

Install with:
```bash
pip3 install requests beautifulsoup4 python-dotenv gspread google-auth
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
- `write_csv(rows, out_path)`: Exports listings to CSV file with UTF-8 BOM encoding
- `upload_to_google_sheets(rows, sheets_url, credentials_path)`: Uploads listings to Google Sheets, clearing existing data first

### Output Format

CSV with columns: `id`, `listing_name`, `price`, `address`, `apart_size`, `link`

### Anti-Scraping Measures

The script uses realistic browser headers (parser.py:23-31) including User-Agent, Accept-Language, and Accept headers to mimic a real browser and reduce likelihood of being blocked.
