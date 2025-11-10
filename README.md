# apart-search-bot

Web scraper for Willhaben.at apartment listings with Playwright for dynamic content loading and Docker support.

## Features

- Scrapes apartment rental listings from Willhaben.at
- Uses Playwright to load dynamic content (scrolls to load all listings)
- Exports data to CSV format
- Fully Dockerized with all dependencies included
- Configurable via `.env` file
- Easy to run with Makefile commands

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker installed on your system
- Make (usually pre-installed on macOS/Linux)

### Usage

1. **Build the Docker image:**
   ```bash
   make build
   ```

2. **Run the scraper:**
   ```bash
   make run
   ```

The CSV file will be saved to `./output/willhaben_listings.csv`

### Available Make Commands

- `make build` - Build Docker image
- `make run` - Run scraper and save CSV to ./output/
- `make run-verbose` - Run with verbose logging
- `make shell` - Open interactive shell in container
- `make clean` - Remove Docker image and output files
- `make rebuild` - Clean and rebuild from scratch
- `make help` - Show all available commands

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

## Local Installation (Without Docker)

If you prefer to run locally without Docker:

### Prerequisites
- Python 3.13+
- pip

### Install Dependencies

```bash
pip3 install -r requirements.txt
playwright install chromium
```

### Run Locally

```bash
# Basic usage
python3 parser.py

# With verbose logging
python3 parser.py --verbose

# Watch browser in action (non-headless mode)
python3 parser.py --no-headless

# Custom output file
python3 parser.py --out my_listings.csv

# Override ROWS parameter
python3 parser.py --rows 500
```

## How It Works

1. **Dynamic Loading**: Uses Playwright to launch a headless Chromium browser
2. **Scrolling**: Automatically scrolls to the bottom of the page to trigger lazy-loading of all listings
3. **Parsing**: Extracts listing data using BeautifulSoup with multi-layered parsing:
   - JSON-LD structured data
   - HTML card parsing with CSS selectors
   - Heuristic-based fallbacks for addresses
4. **Export**: Saves all data to CSV format

## Output Format

CSV with columns:
- `id` - Listing ID
- `listing_name` - Apartment title
- `price` - Monthly rent
- `address` - Location/address
- `apart_size` - Size in m²
- `link` - URL to listing

## Troubleshooting

**Docker issues:**
```bash
# Rebuild from scratch
make rebuild

# Check if Docker is running
docker ps

# View container logs
make logs
```

**No listings found:**
- Check your `.env` configuration
- Try running with `--verbose` flag to see detailed logs
- Verify the search URL parameters are correct

## License

MIT
