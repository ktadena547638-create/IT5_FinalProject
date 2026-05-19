from pathlib import Path
from utils.export_utils import export_products_to_csv
from main import Config


def main():
    db = Config.DB_PATH
    out = Path(db.parent) / "products_export.csv"
    count, path = export_products_to_csv(db, out)
    print(f"Exported {count} rows to {path}")


if __name__ == "__main__":
    main()
