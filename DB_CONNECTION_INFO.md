# Database Connection Information

## Quick Start

Start the database in background mode:
```bash
make up-detached
```

The database will be available at `localhost:5432`

## Connection Details

| Parameter | Value |
|-----------|-------|
| **Host** | `localhost` |
| **Port** | `5432` |
| **Database** | `willhaben` |
| **Username** | `willhaben_user` |
| **Password** | `willhaben_pass` |

## Connection Strings

**PostgreSQL URI:**
```
postgresql://willhaben_user:willhaben_pass@localhost:5432/willhaben
```

**psycopg2 (Python):**
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="willhaben",
    user="willhaben_user",
    password="willhaben_pass"
)
```

**Node.js (pg):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'willhaben',
  user: 'willhaben_user',
  password: 'willhaben_pass'
});
```

**JDBC (Java):**
```
jdbc:postgresql://localhost:5432/willhaben
User: willhaben_user
Password: willhaben_pass
```

## Recommended UI Tools

### pgAdmin (Most Popular)
- Download: https://www.pgadmin.org/download/
- Free, open-source, feature-rich
- Best for: Complex queries, schema design

### DBeaver (Cross-platform)
- Download: https://dbeaver.io/download/
- Supports multiple databases
- Best for: General purpose, beginners

### TablePlus (macOS/Windows/Linux)
- Download: https://tableplus.com/
- Modern, fast, beautiful UI
- Best for: Quick browsing, simple queries

### DataGrip (JetBrains)
- Download: https://www.jetbrains.com/datagrip/
- Paid (free for students)
- Best for: Developers who use IntelliJ

### Postico (macOS only)
- Download: https://eggerapps.at/postico/
- Native macOS app
- Best for: Mac users who want native experience

## Quick Setup Steps

1. **Start database:**
   ```bash
   make up-detached
   ```

2. **Verify it's running:**
   ```bash
   docker ps | grep postgres
   ```

3. **Test connection:**
   ```bash
   make db-console
   ```

4. **Open in your UI tool:**
   - Create new connection
   - Enter the credentials above
   - Click connect!

## Common Commands

```bash
# Start database
make up-detached

# Stop database
make down

# View database logs
make db-logs

# Enter console
make db-console

# Reset database (WARNING: deletes all data)
make db-reset
```

## Database Schema

### Tables

**listings:**
- `link` (TEXT, PRIMARY KEY) - Listing URL
- `id` (VARCHAR) - Listing ID (nullable)
- `listing_name` (TEXT) - Apartment title
- `price` (VARCHAR) - Rental price
- `address` (TEXT) - Location
- `apart_size` (VARCHAR) - Size in m²
- `first_seen_at` (TIMESTAMP) - First scraped
- `last_seen_at` (TIMESTAMP) - Last seen
- `created_at` (TIMESTAMP) - Created
- `updated_at` (TIMESTAMP) - Updated

**scraper_runs:**
- `id` (SERIAL, PRIMARY KEY) - Run ID
- `started_at` (TIMESTAMP) - Start time
- `finished_at` (TIMESTAMP) - End time
- `listings_found` (INTEGER) - Total found
- `new_listings` (INTEGER) - New count
- `updated_listings` (INTEGER) - Updated count
- `status` (VARCHAR) - Status (running/success/failed)
- `error_message` (TEXT) - Error details

## Example Queries

```sql
-- View all listings
SELECT * FROM listings ORDER BY first_seen_at DESC;

-- Count total listings
SELECT COUNT(*) FROM listings;

-- View recent runs
SELECT * FROM scraper_runs ORDER BY started_at DESC;

-- Find listings by district
SELECT * FROM listings WHERE address LIKE '%19. Bezirk%';

-- Get new listings from today
SELECT * FROM listings 
WHERE first_seen_at::date = CURRENT_DATE;
```

## Troubleshooting

**Can't connect?**
1. Check database is running: `docker ps | grep postgres`
2. Check port is exposed: `docker port willhaben-postgres`
3. Verify credentials in `.env` file

**Port already in use?**
- Change port in `.env`: `POSTGRES_PORT=5433`
- Restart: `make down && make up-detached`
- Use new port in UI tool

**Need to change password?**
1. Edit `.env` file
2. Reset database: `make db-reset`
3. Reconnect with new credentials
