"""One-time migration from backend/inventory.xlsx to PostgreSQL.

Usage from backend/:
    set DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
    python migrate_excel_to_postgres.py

The Excel file is read only; it is not deleted or modified.
"""

import os
from pathlib import Path

import pandas as pd

from db import TABLES, DTYPES, get_engine, ensure_schema, write_tables


ROOT = Path(__file__).parent
BOOK = Path(os.getenv("EXCEL_SOURCE", str(ROOT / "inventory.xlsx")))


def read_excel_tables():
    if not BOOK.exists():
        raise FileNotFoundError(f"File Excel tidak ditemukan: {BOOK}")

    tables = {}
    for table, columns in TABLES.items():
        try:
            df = pd.read_excel(BOOK, sheet_name=table)
        except ValueError:
            df = pd.DataFrame(columns=columns)
        tables[table] = df.reindex(columns=columns).fillna("")
    return tables


def main():
    engine = get_engine()
    ensure_schema(engine)
    tables = read_excel_tables()

    print(f"Sumber Excel: {BOOK}")
    for table, df in tables.items():
        print(f"- {table}: {len(df)} baris")

    write_tables(engine, tables)

    # Verify counts after migration.
    with engine.connect() as conn:
        from sqlalchemy import text
        for table in TABLES:
            count = conn.execute(
                text(f'SELECT COUNT(*) FROM "{table}"')
            ).scalar_one()
            print(f"  PostgreSQL {table}: {count} baris")

    print("Migrasi Excel -> PostgreSQL selesai.")


if __name__ == "__main__":
    main()
