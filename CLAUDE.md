# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL RULE: Docker-Only Execution

**NEVER run Python locally. NEVER install dependencies locally. ALWAYS use Docker.**

- ❌ Never run `python3 ...` or `pip install ...` on the host machine
- ❌ Never install packages or dependencies locally
- ✅ Always use `docker-compose run --rm scraper ...` to execute Python code
- ✅ Always use `make build` to rebuild after code changes
- ✅ All testing, running, and dependency management happens inside Docker containers

This project is fully Dockerized. All dependencies are managed within the Docker image.

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

### Running with Docker Compose

**All commands must be run inside Docker containers:**

```bash
# Basic usage
docker-compose run --rm scraper python3 main.py

# With options
docker-compose run --rm scraper python3 main.py --verbose              # Detailed logs
docker-compose run --rm scraper python3 main.py --no-headless          # Show browser
docker-compose run --rm scraper python3 main.py --rows 100             # Override ROWS
docker-compose run --rm scraper python3 main.py --download-photos      # Download photos for new listings
```

## Dependencies

The script requires:
- `playwright` - Browser automation and dynamic content loading
- `beautifulsoup4` - HTML parsing
- `python-dotenv` - Environment variable loading
- `psycopg2-binary` - PostgreSQL database driver
- `requests` - HTTP library for photo downloads
- Standard library: `argparse`, `csv`, `json`, `logging`, `os`, `re`, `sys`, `time`, `urllib.parse`

**All dependencies are pre-installed in the Docker image. No local installation needed.**

To rebuild the Docker image after changes:
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
├── logger.py       # Action logging and tracking
├── database.py     # PostgreSQL database operations
└── photos.py       # Photo downloading for listings

main.py             # CLI entry point
parser.py           # Backward compatibility shim
docker-compose.yml  # Docker Compose with PostgreSQL
init.sql            # Database schema initialization
photos/             # Downloaded listing photos (excluded from git)
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

**`src/database.py`**: PostgreSQL database operations
- `get_database()`: Get singleton database instance
- `upsert_listing()`: Insert or update listing (tracks first_seen/last_seen)
- `save_listings()`: Batch save with new/updated counts
- `start_run()` / `finish_run()`: Track scraper executions
- `get_new_listings_since()`: Query new listings by timestamp
- Connection pooling for performance
- See `DATABASE.md` for complete documentation

**`src/photos.py`**: Photo downloading and storage
- `download_listing_photos(link, listing_name)`: Download all photos for a single listing
- `download_photos_for_listings(listings)`: Batch download photos for multiple listings
- `get_listing_dir(link)`: Get hierarchical directory path for storing photos
- Uses Playwright to fetch listing pages
- Extracts image URLs from gallery and thumbnails
- Stores photos in hierarchical structure: `photos/ab/cd/abcd.../`
- Skips listings that already have downloaded photos
- Creates metadata.txt file with link and listing name

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

### Photo Downloading

The scraper can automatically download photos for new listings when run with `--download-photos` flag:

**Features:**
- Downloads photos only for new listings (first-time discoveries)
- Stores photos in hierarchical directory structure to avoid filesystem limits
- Directory path: `photos/ab/cd/abcd.../` (based on MD5 hash of listing URL)
- Skips listings that already have photos downloaded
- Creates `metadata.txt` file in each listing directory with link and name
- Extracts images from Willhaben gallery and thumbnails
- Filters out tiny thumbnails, keeps high-resolution images only

**Usage:**
```bash
# Enable photo downloading
python3 main.py --download-photos

# Photo downloading in headful mode (see browser)
python3 main.py --download-photos --no-headless
```

**Configuration (via .env):**
- `PHOTOS_DIR` - Base directory for photos (default: `photos`)
- `PHOTO_TIMEOUT` - Page load timeout in ms (default: `10000`)
- `MAX_PHOTOS_PER_LISTING` - Maximum photos per listing (default: `50`)

**Note:** Photo downloading requires database mode (enabled by default). Photos are NOT downloaded in CSV-only mode (`--use-csv`).

## Testing New Listing Detection

The primary purpose of this application is to detect new apartment listings and process them (e.g., send to Telegram, download photos). To test the complete new listing detection and notification flow:

```bash
make test-flow
```

**What it does:**
1. Stops all services (`make down`)
2. Rebuilds and runs initial scrape (`make all`)
3. Deletes the most recent listing from the database (top of search results)
4. Cleans photos directory
5. Starts Telegram bot (detects deleted listing as new, downloads photos, sends notification)

**Why this works:**
This simulates real-world behavior where new listings appear at the top of search results. By deleting the most recent listing and re-scraping, the scraper treats it as a brand new discovery.

**Expected behavior:**
- Deleted listing is re-detected as "new"
- Bot downloads photos to `photos/ab/cd/abcd.../` directory structure
- Bot sends Telegram notification with all photos as media group (album)
- Database tracks `first_seen_at` timestamp

**Verify results:**
1. **Check Telegram channel**: You should receive a notification with listing details and all photos in a single album
2. **Check downloaded photos**: `ls -la photos/`
3. **Check database**:
   ```bash
   make db-console
   SELECT listing_name, first_seen_at, last_seen_at FROM listings ORDER BY first_seen_at DESC LIMIT 5;
   ```

**Stop the test:**
- Press `Ctrl+C` to stop the bot after verifying the notification
- Use `make down` to stop all services
- Use `make bot-up-detached` to restart bot in background for continuous monitoring

Use this command to test the complete end-to-end flow including Telegram notifications.

## Telegram Bot

The Telegram bot runs continuously, checking for new apartment listings at regular intervals and sending notifications to a Telegram channel or chat.

### Setup

**1. Create a Telegram Bot:**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Copy the bot token

**2. Get Chat ID:**
   - Add your bot to a channel or group chat
   - For channels: forward a message from the channel to [@userinfobot](https://t.me/userinfobot)
   - For group chats: add the bot to the group, then forward a message to @userinfobot
   - Copy the chat ID (will be negative for groups/channels)

**3. Configure .env:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
SCRAPER_INTERVAL_MINUTES=5
DOWNLOAD_PHOTOS=true
```

### Running the Bot

**Quick Start - Run everything (recommended):**
```bash
make start-all
```
This command:
1. Starts the database
2. Runs an initial scrape to populate the database with current listings
3. Starts the Telegram bot in background for continuous monitoring

**Start the bot in foreground (see logs):**
```bash
make bot-up
```

**Start the bot in background:**
```bash
make bot-up-detached
```

**View bot logs:**
```bash
make bot-logs
```

**Stop the bot:**
```bash
make bot-down
```

**Restart the bot:**
```bash
make bot-restart
```

**Stop all services (database + bot):**
```bash
make down
```

### How It Works

1. **Periodic Scraping**: Bot runs the scraper every N minutes (configured via `SCRAPER_INTERVAL_MINUTES`)
2. **Smart Scrolling**: Uses intelligent scrolling to stop when reaching already-seen listings
3. **New Listing Detection**: Compares scrape results with database to identify new listings
4. **Photo Downloads**: Automatically downloads photos for new listings (if enabled)
5. **Telegram Notifications**: Sends formatted messages with listing details and photos to configured chat

### Message Format

Each new listing notification includes:
- 🏠 Listing name
- 💰 Price
- 📍 Address
- 📏 Size
- 🔗 Link to listing
- 📸 Photos (up to 10 images)

### Configuration Variables

All configuration is done via `.env` file:

- `TELEGRAM_BOT_TOKEN` - Bot API token from BotFather (required)
- `TELEGRAM_CHAT_ID` - Channel or chat ID to send messages to (required)
- `SCRAPER_INTERVAL_MINUTES` - How often to check for new listings (default: 5)
- `DOWNLOAD_PHOTOS` - Whether to download photos for new listings (default: true)
- `PHOTOS_DIR` - Base directory for storing photos (default: photos)

### Architecture

The bot consists of three main modules:

**`src/telegram_bot.py`**: Telegram messaging
- `TelegramNotifier` class for sending messages and photos
- Message formatting and photo handling
- Rate limiting and error handling

**`src/scheduler.py`**: Periodic scraping orchestration
- `ScraperScheduler` class for running scraper at intervals
- Smart scrolling integration
- New listing detection
- Callback system for notifications

**`bot_main.py`**: Main application entry point
- Initializes bot configuration
- Coordinates scheduler and notifier
- Handles graceful shutdown
- Runs continuously with restart policy

### Docker Service

The bot runs as a separate Docker service (`bot`) defined in `docker-compose.yml`:
- Runs continuously with `restart: unless-stopped` policy
- Shares database with scraper service
- Mounts same volumes for photos and output
- Auto-starts on system boot (if Docker is configured)

### Testing

To test the bot with the new listing detection flow:

```bash
# 1. Set up your bot token and chat ID in .env
# 2. Run test flow (will trigger bot notification)
make test-flow

# 3. Check your Telegram channel for the notification
```

Or test the bot manually:
```bash
# Start the bot
make bot-up-detached

# Delete a recent listing to simulate a new one
make db-console
DELETE FROM listings WHERE link = (SELECT link FROM listings ORDER BY first_seen_at DESC LIMIT 1);
\q

# Wait for next scraper run (max 5 minutes)
# Check Telegram channel for notification
make bot-logs
```

### Troubleshooting

**Bot not sending messages:**
- Check bot token and chat ID are correct in `.env`
- Verify bot has permission to post in the channel
- Check bot logs: `make bot-logs`

**No new listings detected:**
- Database might already have all listings
- Use `make test-flow` to simulate new listings
- Check scraper logs for errors

**Photos not downloading:**
- Ensure `DOWNLOAD_PHOTOS=true` in `.env`
- Check disk space in `photos/` directory
- Verify Playwright can access listing pages
