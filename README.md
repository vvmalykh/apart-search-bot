# apart-search-bot

Web scraper for Willhaben.at apartment listings with Google Sheets integration.

## Features

- Scrapes apartment rental listings from Willhaben.at
- Exports data to CSV format
- Automatically uploads to Google Sheets (optional)
- Configurable search parameters

## Installation

```bash
pip3 install requests beautifulsoup4 python-dotenv gspread google-auth
```

## Quick Start

```bash
# Basic usage (CSV export only)
python3 parser.py

# With custom search URL
python3 parser.py --url "https://www.willhaben.at/iad/immobilien/..."
```

## Google Sheets Setup

1. **Create Google Cloud Service Account:**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Google Sheets API and Google Drive API
   - Create a Service Account and download JSON credentials
   - Save as `credentials.json` in project root

2. **Configure `.env` file:**
   ```bash
   GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
   ```

3. **Share your Google Sheet:**
   - Find the `client_email` in `credentials.json`
   - Share your Google Sheet with this email (Editor permission)

4. **Run the script:**
   ```bash
   python3 parser.py
   ```

## Command-Line Options

- `--url` - Willhaben search URL (default: predefined search)
- `--rows` - Number of results per page (default: 10000)
- `--out` - Output CSV file path (default: willhaben_listings.csv)
- `--credentials` - Path to Google credentials JSON (default: credentials.json)
- `--no-sheets` - Disable Google Sheets upload

## Output Format

CSV with columns:
- `id` - Listing ID
- `listing_name` - Apartment title
- `price` - Rent price
- `address` - Location
- `apart_size` - Size in m²
- `link` - URL to listing

## License

MIT
