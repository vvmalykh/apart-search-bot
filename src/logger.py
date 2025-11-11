"""
Logging module for tracking all major actions in the apartment scraper.

Logs are stored in output/scraper.log with human-friendly formatting.
Each new run appends to existing logs (doesn't erase previous logs).
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class ActionLogger:
    """Logger for tracking scraper actions with human-friendly formatting."""

    def __init__(self, log_file: str = "output/scraper.log"):
        """
        Initialize the action logger.

        Args:
            log_file: Path to log file (default: output/scraper.log)
        """
        self.log_file = log_file
        self._ensure_output_dir()
        self._setup_logger()

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        output_dir = Path(self.log_file).parent
        output_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logger(self) -> None:
        """Configure the logger with human-friendly formatting."""
        # Create custom logger
        self.logger = logging.getLogger("scraper_actions")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler (append mode to preserve previous logs)
        file_handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # Human-friendly format: [2025-11-11 19:30:45] ACTION: description
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'  # 24-hour format
        )
        file_handler.setFormatter(formatter)

        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _log(self, level: str, action: str, details: str = "") -> None:
        """
        Internal logging method.

        Args:
            level: Log level (INFO, WARNING, ERROR)
            action: Action name/description
            details: Additional details (optional)
        """
        message = f"{action}"
        if details:
            message += f" - {details}"

        if level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)

    def separator(self) -> None:
        """Add a visual separator in logs (for new run)."""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*80 + "\n")

    # ==================== Current Actions ====================

    def app_init(self, details: str = "") -> None:
        """Log application initialization."""
        self.separator()
        self._log("INFO", "APP INITIALIZED", details)

    def parsing_started(self, url: str = "") -> None:
        """Log parsing started."""
        details = f"URL: {url}" if url else ""
        self._log("INFO", "PARSING STARTED", details)

    def open_site(self, url: str) -> None:
        """Log opening website."""
        self._log("INFO", "OPENING SITE", url)

    def site_loaded(self, duration_ms: int = None) -> None:
        """Log site loaded (after internal pause)."""
        details = f"Wait time: {duration_ms}ms" if duration_ms else ""
        self._log("INFO", "SITE LOADED", details)

    def scrolling_finished(self, scroll_count: int = None) -> None:
        """Log scrolling finished."""
        details = f"Scrolls: {scroll_count}" if scroll_count else ""
        self._log("INFO", "SCROLLING FINISHED", details)

    def records_added(self, count: int) -> None:
        """Log records added to CSV."""
        self._log("INFO", "RECORDS ADDED", f"{count} listings")

    # ==================== Future Actions ====================

    def new_listing_detected(self, title: str = "") -> None:
        """Log new listing detected."""
        details = f"Title: {title}" if title else "New listing"
        self._log("INFO", "NEW LISTING DETECTED", details)

    def listing_opened(self, listing_id: str, url: str = "") -> None:
        """Log listing page opened."""
        details = f"ID: {listing_id}"
        if url:
            details += f", URL: {url}"
        self._log("INFO", "LISTING OPENED", details)

    def telegram_message_sent(self, listing_id: str, success: bool = True) -> None:
        """Log Telegram message sent."""
        level = "INFO" if success else "ERROR"
        status = "SUCCESS" if success else "FAILED"
        self._log(level, "TELEGRAM MESSAGE SENT", f"ID: {listing_id}, Status: {status}")

    def telegram_action_received(self, action: str, listing_id: str = "") -> None:
        """
        Log action received from Telegram.

        Args:
            action: Action type (cancel, send_email, etc.)
            listing_id: Listing ID (optional)
        """
        details = f"Action: {action.upper()}"
        if listing_id:
            details += f", ID: {listing_id}"
        self._log("INFO", "TELEGRAM ACTION RECEIVED", details)

    def email_sent(self, recipient: str, listing_id: str = "", success: bool = True) -> None:
        """Log email sent to host."""
        level = "INFO" if success else "ERROR"
        status = "SUCCESS" if success else "FAILED"
        details = f"To: {recipient}, Status: {status}"
        if listing_id:
            details += f", ID: {listing_id}"
        self._log(level, "EMAIL SENT", details)

    # ==================== Generic/Error Logging ====================

    def info(self, message: str) -> None:
        """Log generic info message."""
        self._log("INFO", message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self._log("WARNING", message)

    def error(self, message: str, exception: Exception = None) -> None:
        """Log error message."""
        details = str(exception) if exception else message
        self._log("ERROR", "ERROR", details)

    def custom_action(self, action_name: str, details: str = "") -> None:
        """
        Log custom action (for extensibility).

        Args:
            action_name: Name of the custom action
            details: Additional details
        """
        self._log("INFO", action_name.upper(), details)


# Global logger instance
_logger_instance = None


def get_logger(log_file: str = "output/scraper.log") -> ActionLogger:
    """
    Get or create the global logger instance.

    Args:
        log_file: Path to log file (default: output/scraper.log)

    Returns:
        ActionLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ActionLogger(log_file)
    return _logger_instance
