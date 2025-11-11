# Logging Documentation

## Overview

The scraper includes a comprehensive action logging system that tracks all major operations. Logs are stored in `output/scraper.log` with human-friendly formatting and are preserved across multiple runs (append mode).

## Log Format

Each log entry follows this format:
```
[YYYY-MM-DD HH:MM:SS] LEVEL: ACTION - Details
```

Example:
```
[2025-11-11 19:23:38] INFO: APP INITIALIZED - Version: MVP, Output: willhaben_listings.csv
[2025-11-11 19:23:38] INFO: PARSING STARTED - URL: https://www.willhaben.at/...
[2025-11-11 19:23:39] INFO: OPENING SITE - https://www.willhaben.at/...
[2025-11-11 19:23:41] INFO: SITE LOADED - Wait time: 2000ms
[2025-11-11 19:23:55] INFO: SCROLLING FINISHED - Scrolls: 15
[2025-11-11 19:23:56] INFO: RECORDS ADDED - 42 listings
```

Each new run is separated by a visual separator line (`================`).

## Usage

### Import the Logger

```python
from src.logger import get_logger

# Get logger instance (singleton)
logger = get_logger()
```

### Current Actions

These actions are already implemented and logging:

```python
# Application lifecycle
logger.app_init("Version: 1.0")
logger.parsing_started("https://www.example.com")

# Browser automation
logger.open_site("https://www.example.com")
logger.site_loaded(2000)  # duration in ms
logger.scrolling_finished(15)  # scroll count

# Data processing
logger.records_added(42)  # number of records
```

### Future Actions

Pre-built methods for upcoming features:

```python
# Listing detection
logger.new_listing_detected("12345", "Apartment Title")
logger.listing_opened("12345", "https://...")

# Telegram integration
logger.telegram_message_sent("12345", success=True)
logger.telegram_action_received("cancel", "12345")
logger.telegram_action_received("send_email", "12345")

# Email integration
logger.email_sent("host@example.com", "12345", success=True)
```

### Generic Logging

For custom events or errors:

```python
# Info/Warning/Error
logger.info("Custom message")
logger.warning("Something might be wrong")
logger.error("Error occurred", exception_obj)

# Custom actions
logger.custom_action("MY_ACTION", "Details here")
```

## Log Levels

- **INFO**: Normal operations (green in console)
- **WARNING**: Potential issues (yellow in console)
- **ERROR**: Errors and exceptions (red in console)

## Log Location

**Default**: `output/scraper.log`

**Custom location**:
```python
logger = get_logger("custom/path/mylog.log")
```

## Features

✅ **Append mode**: New runs don't erase previous logs
✅ **Visual separators**: Each run clearly separated
✅ **24-hour format**: Hours:Minutes:Seconds
✅ **Human-friendly**: Easy to read timestamps and messages
✅ **Dual output**: Logs to both file and console
✅ **Extensible**: Easy to add new action types

## Adding New Actions

To add a new action type:

1. Open `src/logger.py`
2. Add a new method in the `ActionLogger` class:

```python
def my_new_action(self, param1: str, param2: int = None) -> None:
    """Log my new action."""
    details = f"Param1: {param1}"
    if param2:
        details += f", Param2: {param2}"
    self._log("INFO", "MY_NEW_ACTION", details)
```

3. Use it anywhere:

```python
from src.logger import get_logger
logger = get_logger()
logger.my_new_action("value1", 123)
```

## Example Log Output

```
================================================================================
[2025-11-11 19:23:38] INFO: APP INITIALIZED - Version: MVP, Output: listings.csv
[2025-11-11 19:23:38] INFO: PARSING STARTED - URL: https://www.willhaben.at/iad/...
[2025-11-11 19:23:39] INFO: OPENING SITE - https://www.willhaben.at/iad/...
[2025-11-11 19:23:41] INFO: SITE LOADED - Wait time: 2000ms
[2025-11-11 19:23:55] INFO: SCROLLING FINISHED - Scrolls: 15
[2025-11-11 19:23:56] INFO: RECORDS ADDED - 42 listings

================================================================================
[2025-11-11 20:15:22] INFO: APP INITIALIZED - Version: MVP, Output: listings.csv
[2025-11-11 20:15:22] INFO: NEW LISTING DETECTED - ID: 12345, Title: 2-Zimmer Wohnung
[2025-11-11 20:15:23] INFO: TELEGRAM MESSAGE SENT - ID: 12345, Status: SUCCESS
[2025-11-11 20:15:45] INFO: TELEGRAM ACTION RECEIVED - Action: SEND_EMAIL, ID: 12345
[2025-11-11 20:15:46] INFO: EMAIL SENT - To: host@example.com, Status: SUCCESS, ID: 12345
```

## Integration with Existing Code

The logger is already integrated into:
- `main.py` - App initialization, parsing started, records added
- `src/scraper.py` - Site opening, loading, scrolling
- All error handling

Ready for future integrations:
- Telegram bot notifications
- Email sending
- Listing detection and tracking
