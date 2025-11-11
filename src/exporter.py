"""CSV export functionality for listing data."""

import csv
import logging

from .config import CSV_FIELDS

logger = logging.getLogger(__name__)


def write_csv(rows: list[dict[str, str]], out_path: str) -> None:
    """
    Write listing data to CSV file.

    Args:
        rows: List of listing dictionaries
        out_path: Path to output CSV file

    Raises:
        IOError: If file cannot be written
    """
    try:
        with open(out_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
        logger.info(f"Wrote {len(rows)} listings to {out_path}")
    except IOError as e:
        logger.error(f"Failed to write CSV file {out_path}: {e}")
        raise
