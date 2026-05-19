import csv
import sqlite3
from pathlib import Path
import tempfile

from utils.export_utils import export_products_to_csv


def create_sample_db(path: Path):
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            price REAL,
            cost_price REAL,
            quantity INTEGER
        )
        """
    )
    cur.executemany("INSERT INTO products (sku, name, brand, price, cost_price, quantity) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        ("A-001", "Test Item 1", "BrandX", 10.5, 7.0, 5),
                        ("A-002", "Test Item 2", "BrandY", 20.0, 12.5, 3),
                    ])
    conn.commit()
    conn.close()


def test_export_creates_csv(tmp_path: Path):
    db_file = tmp_path / "test.db"
    create_sample_db(db_file)

    out_file = tmp_path / "out.csv"
    count, path = export_products_to_csv(db_file, out_file)

    assert count == 2
    assert path.exists()

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # header + 2 rows
    assert len(rows) == 3
    assert rows[0][0].lower() == "sku"
