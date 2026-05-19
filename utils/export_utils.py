import csv
import os
import sqlite3
import time
from pathlib import Path
from typing import Tuple


def _atomic_write_lines(out_path: Path, header: list, rows_iter, retries: int = 3, delay: float = 0.1):
    """Write CSV atomically: write to temp file then replace.

    Retries replace on Windows to avoid transient lock errors.
    """
    out_path = Path(out_path)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    # Write to temp file
    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows_iter:
            writer.writerow(row)
        f.flush()
        os.fsync(f.fileno())

    # Replace atomically (os.replace should be atomic)
    last_exc = None
    for attempt in range(retries):
        try:
            os.replace(str(tmp_path), str(out_path))
            return
        except Exception as e:
            last_exc = e
            time.sleep(delay * (attempt + 1))

    # final attempt without swallow
    if tmp_path.exists():
        # try one last time
        os.replace(str(tmp_path), str(out_path))


def export_products_to_csv(db_path: Path, out_path: Path, chunk_size: int = 500) -> Tuple[int, Path]:
    """Export the `products` table from SQLite at db_path to CSV at out_path.

    Uses chunked fetch to avoid large memory usage and atomic write to avoid partial files.

    Returns (row_count, out_path).
    Raises exceptions on failure.
    """
    db_path = Path(db_path)
    out_path = Path(out_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    conn = None
    try:
        # Connect with a timeout and detect transient locks
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        if not cur.fetchone():
            raise RuntimeError("No 'products' table in database")

        cur.execute("SELECT * FROM products")

        # Prepare header from cursor description
        cols = [d[0] for d in cur.description]

        def row_generator():
            while True:
                chunk = cur.fetchmany(chunk_size)
                if not chunk:
                    break
                for r in chunk:
                    # Convert sqlite3.Row to list preserving order
                    yield [r[c] for c in cols]

        # Write atomically
        _atomic_write_lines(out_path, cols, row_generator())

        # Determine total rows (re-open cursor to count)
        cur.execute("SELECT COUNT(*) as cnt FROM products")
        total = cur.fetchone()[0]
        return int(total), out_path

    finally:
        if conn:
            conn.close()
