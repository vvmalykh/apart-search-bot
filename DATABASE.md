# Database Documentation

## Overview

The scraper now uses PostgreSQL for persistent storage of apartment listings. This enables:

- ✅ Tracking new listings over time
- ✅ Detecting when listings are first seen
- ✅ Monitoring scraper runs
- ✅ Avoiding duplicate data
- ✅ Historical data analysis

## Architecture

### Database Schema

**listings** table:
- `link` - Listing URL (primary key, always unique)
- `id` - Listing ID from Willhaben (nullable, some listings don't have IDs)
- `listing_name` - Apartment title
- `price` - Rental price
- `address` - Location/address
- `apart_size` - Size in m²
- `first_seen_at` - When first scraped
- `last_seen_at` - When last scraped
- `created_at` - Record creation timestamp
- `updated_at` - Record update timestamp

**Note**: `link` is used as the primary key because it's always present and unique, while `id` can be missing for some listings.

**scraper_runs** table:
- `id` - Run ID (auto-increment)
- `started_at` - Run start time
- `finished_at` - Run end time
- `listings_found` - Total listings in run
- `new_listings` - Count of new listings
- `updated_listings` - Count of updated listings
- `status` - Run status (running/success/failed)
- `error_message` - Error details if failed

## Quick Start

### 1. Start Database

```bash
# Start database in background
make up-detached

# Or start with scraper
make up
```

### 2. Run Scraper

```bash
# Run locally with database
make run-with-db

# Or run in docker-compose
make up
```

### 3. Access Database

```bash
# Enter PostgreSQL console
make db-console
```

Inside psql:
```sql
-- View recent listings
SELECT id, listing_name, price, address, first_seen_at
FROM listings
ORDER BY first_seen_at DESC
LIMIT 10;

-- View scraper runs
SELECT id, started_at, listings_found, new_listings, status
FROM scraper_runs
ORDER BY started_at DESC;

-- Count total listings
SELECT COUNT(*) FROM listings;

-- Find new listings from today
SELECT COUNT(*)
FROM listings
WHERE first_seen_at::date = CURRENT_DATE;

-- Exit psql
\q
```

## Make Commands

### Database Management

```bash
make up              # Start database + scraper
make up-detached     # Start database only (background)
make down            # Stop all services
make db-console      # Enter PostgreSQL console
make db-logs         # Show database logs
make db-reset        # Reset database (deletes all data)
make run-with-db     # Run scraper locally with DB
```

### Legacy Commands (CSV only)

```bash
make build           # Build Docker image
make run             # Run scraper without database
```

## Configuration

Database settings in `.env`:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=willhaben
POSTGRES_USER=willhaben_user
POSTGRES_PASSWORD=willhaben_pass
```

**In Docker Compose**: `POSTGRES_HOST=postgres` (service name)
**Locally**: `POSTGRES_HOST=localhost`

## CLI Options

```bash
# Default: Use database
python3 main.py

# Force CSV mode
python3 main.py --use-csv

# Skip database (for testing)
python3 main.py --no-db

# CSV backup with custom filename
python3 main.py --out custom.csv
```

## How It Works

### Upsert Logic

When saving listings:

1. **Check if listing exists** (by `link`)
2. **If new**: Insert with `first_seen_at` = now
3. **If exists**:
   - Compare data fields
   - Update if changed + set `last_seen_at` = now
   - Otherwise just update `last_seen_at`

### Run Tracking

Each scraper execution:

1. Creates a `scraper_runs` record with status='running'
2. Processes and saves listings
3. Updates run record with results and status='success'

### New Listing Detection

```python
from src.database import get_database
from datetime import datetime, timedelta

db = get_database()

# Get listings from last 24 hours
yesterday = datetime.now() - timedelta(days=1)
new_listings = db.get_new_listings_since(yesterday)

for listing in new_listings:
    print(f"New: {listing['listing_name']}")
```

## Database Queries

### Useful SQL Queries

```sql
-- Top 10 most recent listings
SELECT link, id, listing_name, price, address, first_seen_at
FROM listings
ORDER BY first_seen_at DESC
LIMIT 10;

-- Listings by district (Vienna)
SELECT address, COUNT(*) as count
FROM listings
WHERE address LIKE '%Wien%'
GROUP BY address
ORDER BY count DESC;

-- Price statistics
SELECT
  AVG(CAST(REGEXP_REPLACE(price, '[^0-9]', '', 'g') AS INTEGER)) as avg_price,
  MIN(CAST(REGEXP_REPLACE(price, '[^0-9]', '', 'g') AS INTEGER)) as min_price,
  MAX(CAST(REGEXP_REPLACE(price, '[^0-9]', '', 'g') AS INTEGER)) as max_price
FROM listings
WHERE price ~ '^€ [0-9]';

-- Scraper performance
SELECT
  DATE(started_at) as date,
  COUNT(*) as runs,
  SUM(new_listings) as total_new,
  AVG(listings_found) as avg_found
FROM scraper_runs
WHERE status = 'success'
GROUP BY DATE(started_at)
ORDER BY date DESC;
```

## Troubleshooting

### Connection Issues

```bash
# Check if database is running
docker ps | grep postgres

# Check logs
make db-logs

# Restart database
make down
make up-detached
```

### Reset Database

```bash
# WARNING: Deletes all data
make db-reset
```

### Force CSV Mode

If database is unavailable:

```bash
python3 main.py --use-csv --out listings.csv
```

## Docker Volumes

Data persists in Docker volume: `willhaben_postgres_data`

```bash
# List volumes
docker volume ls | grep willhaben

# Remove volume (deletes all data)
docker volume rm willhaben_postgres_data
```

## Migration from CSV

The scraper automatically falls back to CSV if database connection fails. You can:

1. Start with database: `make run-with-db`
2. Fallback happens automatically on error
3. CSV saved to `output/willhaben_listings.csv`

## Next Steps

For future Telegram bot integration:
- Query `get_new_listings_since()` to find new listings
- Send notifications for new listings
- Track which listings were sent via additional table
