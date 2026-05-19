import csv
import sqlite3
from pathlib import Path
from typing import Tuple


def export_products_to_csv(db_path: Path, out_path: Path) -> Tuple[int, Path]:
    """Export the `products` table from SQLite at db_path to CSV at out_path.

    Returns (row_count, out_path).
    Raises exceptions on failure.
    """
    db_path = Path(db_path)
    out_path = Path(out_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    if not cur.fetchone():
        conn.close()
        raise RuntimeError("No 'products' table in database")

    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            writer.writerow([r[c] for c in cols])

    conn.close()
    return len(rows), out_path
