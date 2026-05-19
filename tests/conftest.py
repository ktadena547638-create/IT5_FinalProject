"""Test fixtures and database manager for Inventory System tests.

Provides a temporary SQLite database with schema initialization
for unit testing repositories and application logic.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path

from main import SQLiteDriver


class DBManager:
    """Lightweight DB manager for tests using a temporary SQLite file.

    This avoids nested in-memory transactions by creating a single file-backed
    database and creating fresh connections per context manager call.
    """

    def __init__(self):
        with tempfile.NamedTemporaryFile(
            prefix="inventory_test_", suffix=".db", delete=False
        ) as tmp:
            self.db_path = Path(tmp.name)

        # Initialize schema using a temporary connection
        driver = SQLiteDriver(self.db_path)
        driver.connect()
        driver.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                sku TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT DEFAULT '',
                price REAL NOT NULL,
                cost_price REAL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                category TEXT DEFAULT '',
                supplier TEXT DEFAULT '',
                image_path TEXT DEFAULT '',
                min_stock INTEGER DEFAULT 5,
                total_sold INTEGER DEFAULT 0,
                last_sold_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                username TEXT PRIMARY KEY,
                theme TEXT,
                language TEXT,
                dashboard_view TEXT,
                notifications_enabled INTEGER,
                updated_at TIMESTAMP
            );
            """)
        driver.close()

    @contextmanager
    def get_connection(self):
        driver = SQLiteDriver(self.db_path)
        driver.connect()
        driver.begin()
        try:
            yield driver
        finally:
            driver.commit()
            driver.close()
