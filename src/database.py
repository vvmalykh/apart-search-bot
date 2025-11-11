"""
PostgreSQL database operations for storing apartment listings.

Uses psycopg2 for database connectivity.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict
import logging

import psycopg2
from psycopg2 import pool, extras

from .logger import get_logger

logger = logging.getLogger(__name__)
action_logger = get_logger()


class Database:
    """PostgreSQL database handler for apartment listings."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
        min_connections: int = 1,
        max_connections: int = 10,
    ):
        """
        Initialize database connection pool.

        Args:
            host: Database host (default: from POSTGRES_HOST env)
            port: Database port (default: from POSTGRES_PORT env)
            database: Database name (default: from POSTGRES_DB env)
            user: Database user (default: from POSTGRES_USER env)
            password: Database password (default: from POSTGRES_PASSWORD env)
            min_connections: Minimum pool size
            max_connections: Maximum pool size
        """
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DB", "willhaben")
        self.user = user or os.getenv("POSTGRES_USER", "willhaben_user")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "willhaben_pass")

        self.connection_pool = None
        self.min_connections = min_connections
        self.max_connections = max_connections

    def connect(self) -> None:
        """Create connection pool."""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                self.min_connections,
                self.max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            logger.info(f"Connected to PostgreSQL database: {self.database}")
            action_logger.custom_action("DATABASE_CONNECTED", f"Host: {self.host}, DB: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            action_logger.error("Database connection failed", e)
            raise

    def get_connection(self):
        """Get connection from pool."""
        if not self.connection_pool:
            self.connect()
        return self.connection_pool.getconn()

    def return_connection(self, conn) -> None:
        """Return connection to pool."""
        if self.connection_pool:
            self.connection_pool.putconn(conn)

    def close_all(self) -> None:
        """Close all connections in pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Closed all database connections")

    def start_run(self) -> int:
        """
        Start a new scraper run.

        Returns:
            Run ID
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scraper_runs (started_at, status) VALUES (CURRENT_TIMESTAMP, 'running') RETURNING id"
            )
            run_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            action_logger.custom_action("SCRAPER_RUN_STARTED", f"Run ID: {run_id}")
            return run_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to start run: {e}")
            raise
        finally:
            self.return_connection(conn)

    def finish_run(
        self,
        run_id: int,
        listings_found: int,
        new_listings: int,
        updated_listings: int,
        status: str = "success",
        error_message: str = None,
    ) -> None:
        """
        Finish a scraper run.

        Args:
            run_id: Run ID
            listings_found: Total listings found
            new_listings: Number of new listings
            updated_listings: Number of updated listings
            status: Run status (success/failed)
            error_message: Error message if failed
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE scraper_runs
                SET finished_at = CURRENT_TIMESTAMP,
                    listings_found = %s,
                    new_listings = %s,
                    updated_listings = %s,
                    status = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (listings_found, new_listings, updated_listings, status, error_message, run_id),
            )
            conn.commit()
            cursor.close()
            action_logger.custom_action(
                "SCRAPER_RUN_FINISHED",
                f"Run ID: {run_id}, Status: {status}, Found: {listings_found}, New: {new_listings}"
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to finish run: {e}")
            raise
        finally:
            self.return_connection(conn)

    def upsert_listing(self, listing: Dict[str, str]) -> tuple[bool, bool]:
        """
        Insert or update a listing.

        Args:
            listing: Listing data dictionary

        Returns:
            Tuple of (is_new, was_updated)
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Check if listing exists (using link as primary key)
            cursor.execute("SELECT id, listing_name, price, address, apart_size FROM listings WHERE link = %s", (listing["link"],))
            existing = cursor.fetchone()

            # Normalize empty ID to None for database
            listing_id = listing.get("id")
            if listing_id == "":
                listing_id = None

            if existing:
                # Check if any fields changed
                existing_data = {
                    "id": existing[0],
                    "listing_name": existing[1],
                    "price": existing[2],
                    "address": existing[3],
                    "apart_size": existing[4],
                }

                # Compare data (excluding link)
                has_changes = False
                for key in ["id", "listing_name", "price", "address", "apart_size"]:
                    current_value = listing_id if key == "id" else listing.get(key)
                    if existing_data.get(key) != current_value:
                        has_changes = True
                        break

                if has_changes:
                    # Update existing listing
                    cursor.execute(
                        """
                        UPDATE listings
                        SET id = %s, listing_name = %s, price = %s, address = %s,
                            apart_size = %s, last_seen_at = CURRENT_TIMESTAMP
                        WHERE link = %s
                        """,
                        (
                            listing_id,
                            listing["listing_name"],
                            listing["price"],
                            listing["address"],
                            listing["apart_size"],
                            listing["link"],
                        ),
                    )
                    conn.commit()
                    cursor.close()
                    return (False, True)  # Not new, was updated
                else:
                    # Just update last_seen_at
                    cursor.execute(
                        "UPDATE listings SET last_seen_at = CURRENT_TIMESTAMP WHERE link = %s",
                        (listing["link"],)
                    )
                    conn.commit()
                    cursor.close()
                    return (False, False)  # Not new, not updated
            else:
                # Insert new listing (link is primary key, id can be NULL)
                cursor.execute(
                    """
                    INSERT INTO listings (link, id, listing_name, price, address, apart_size)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        listing["link"],
                        listing_id,
                        listing["listing_name"],
                        listing["price"],
                        listing["address"],
                        listing["apart_size"],
                    ),
                )
                conn.commit()
                cursor.close()

                # Log new listing detection
                action_logger.new_listing_detected(
                    listing_id or "no-id",
                    listing.get("listing_name", "")
                )

                return (True, False)  # Is new, not updated

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert listing: {e}")
            raise
        finally:
            self.return_connection(conn)

    def save_listings(self, listings: List[Dict[str, str]]) -> tuple[int, int]:
        """
        Save multiple listings to database.

        Args:
            listings: List of listing dictionaries

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0

        for listing in listings:
            is_new, was_updated = self.upsert_listing(listing)
            if is_new:
                new_count += 1
            elif was_updated:
                updated_count += 1

        logger.info(f"Saved {len(listings)} listings: {new_count} new, {updated_count} updated")
        return (new_count, updated_count)

    def get_recent_listings(self, limit: int = 100) -> List[Dict[str, str]]:
        """
        Get recent listings.

        Args:
            limit: Maximum number of listings to return

        Returns:
            List of listing dictionaries
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(
                """
                SELECT link, id, listing_name, price, address, apart_size,
                       first_seen_at, last_seen_at
                FROM listings
                ORDER BY first_seen_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        finally:
            self.return_connection(conn)

    def get_new_listings_since(self, timestamp: datetime) -> List[Dict[str, str]]:
        """
        Get listings first seen after a given timestamp.

        Args:
            timestamp: Cutoff timestamp

        Returns:
            List of new listing dictionaries
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(
                """
                SELECT link, id, listing_name, price, address, apart_size,
                       first_seen_at, last_seen_at
                FROM listings
                WHERE first_seen_at > %s
                ORDER BY first_seen_at DESC
                """,
                (timestamp,),
            )
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        finally:
            self.return_connection(conn)


# Global database instance
_db_instance = None


def get_database() -> Database:
    """
    Get or create the global database instance.

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.connect()
    return _db_instance
