# apart-search-bot

Web scraper for Willhaben.at apartment listings with configurable search parameters.

## Features

- Scrapes apartment rental listings from Willhaben.at
- Exports data to CSV format
- Configurable via `.env` file
- Supports custom search URLs and parameters

## Installation

```bash
pip3 install requests beautifulsoup4 python-dotenv
```

## Configuration

Create a `.env` file in the project root:

```env
# Willhaben Configuration
BASE_URL=https://www.willhaben.at
LISTING_PATH=/iad/immobilien/mietwohnungen/mietwohnung-angebote

# Query parameters
ROWS=10000
SORT=1
IS_NAVIGATION=true
SF_ID=81997263-28bb-4349-977e-ca13391b025e

# Area IDs (comma-separated) - Vienna districts
AREA_IDS=117225,117239,117240,117241

# Number of rooms buckets (comma-separated)
NO_OF_ROOMS_BUCKETS=2X2,3X3,4X4,5X5

# Property types (comma-separated)
PROPERTY_TYPES=110,102,3

# Filters
PAGE=1
PRICE_TO=2000
ESTATE_SIZE_FROM=45
```

**Configuration Guide:**
- `ROWS` - Results per page (max 10000)
- `AREA_IDS` - Vienna district codes
- `NO_OF_ROOMS_BUCKETS` - 2X2=2 rooms, 3X3=3 rooms, etc.
- `PRICE_TO` - Maximum monthly rent
- `ESTATE_SIZE_FROM` - Minimum apartment size in m²

## Usage

**Basic usage (uses .env configuration):**
```bash
python3 parser.py
```

**With custom URL:**
```bash
python3 parser.py --url "https://www.willhaben.at/iad/immobilien/..."
```

**Override ROWS parameter:**
```bash
python3 parser.py --rows 500
```

**Custom output file:**
```bash
python3 parser.py --out results.csv
```

## Output Format

CSV with columns:
- `id` - Listing ID
- `listing_name` - Apartment title
- `price` - Monthly rent
- `address` - Location/address
- `apart_size` - Size in m²
- `link` - URL to listing

## License

MIT
