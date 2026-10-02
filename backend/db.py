"""PostgreSQL storage adapter for Stock-Mandiri.

The API layer still uses pandas DataFrames so the existing response shapes remain
compatible with the frontend. PostgreSQL is the runtime source of truth.
"""

import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.types import Boolean, Float, Integer, Text
from dotenv import load_dotenv


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


TABLES = {
    "products": [
        "id", "sku", "barcode", "name", "short_name", "category", "brand", "model",
        "unit", "cost_price", "sell_price", "online_price", "stock", "min_stock",
        "location", "supplier", "active", "created_at", "updated_at",
    ],
    "movements": [
        "id", "transaction_no", "sku", "product", "type", "qty_in", "qty_out",
        "before", "after", "price", "note", "user", "created_at",
    ],
    "sales": [
        "id", "invoice", "date", "customer", "sku", "product", "qty", "sell_price",
        "discount", "total", "cost_total", "status", "payment_status",
        "payment_method", "sales", "note", "due_date",
    ],
}

DTYPES = {
    "products": {
        **{c: Text() for c in [
            "id", "sku", "barcode", "name", "short_name", "category", "brand", "model",
            "unit", "location", "supplier", "created_at", "updated_at",
        ]},
        **{c: Float() for c in ["cost_price", "sell_price", "online_price"]},
        **{c: Integer() for c in ["stock", "min_stock"]},
        "active": Boolean(),
    },
    "movements": {
        **{c: Text() for c in [
            "id", "transaction_no", "sku", "product", "type", "note", "user", "created_at",
        ]},
        **{c: Integer() for c in ["qty_in", "qty_out", "before", "after"]},
        "price": Float(),
    },
    "sales": {
        **{c: Text() for c in [
            "id", "invoice", "date", "customer", "sku", "product", "status",
            "payment_status", "payment_method", "sales", "note", "due_date",
        ]},
        "qty": Integer(),
        **{c: Float() for c in ["sell_price", "discount", "total", "cost_total"]},
    },
}


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL belum diatur. Contoh: "
            "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME"
        )
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def get_engine():
    return create_engine(
        database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def _empty_frame(table: str) -> pd.DataFrame:
    return pd.DataFrame(columns=TABLES[table])


def ensure_schema(engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in TABLES.items():
            if not inspector.has_table(table):
                _empty_frame(table).to_sql(
                    table,
                    con=conn,
                    index=False,
                    dtype=DTYPES[table],
                )

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_products_sku "
            "ON products (sku)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_movements_sku "
            "ON movements (sku)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_sales_invoice "
            "ON sales (invoice)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_sales_date "
            "ON sales (date)"
        ))


def read_table(engine, table: str) -> pd.DataFrame:
    if table not in TABLES:
        raise ValueError(f"Tabel tidak dikenal: {table}")
    with engine.connect() as conn:
        df = pd.read_sql(text(f'SELECT * FROM "{table}"'), conn)
    return df.reindex(columns=TABLES[table]).fillna("")


def write_tables(engine, tables: Dict[str, pd.DataFrame]) -> None:
    """Replace the three logical tables in one PostgreSQL transaction.

    The current API was originally designed around whole-workbook writes.
    This adapter preserves that behavior while moving persistence to PostgreSQL.
    """
    with engine.begin() as conn:
        for table in TABLES:
            if table not in tables:
                continue
            df = tables[table].reindex(columns=TABLES[table]).copy().fillna("")
            conn.execute(text(f'DELETE FROM "{table}"'))
            if not df.empty:
                df.to_sql(
                    table,
                    con=conn,
                    index=False,
                    if_exists="append",
                    dtype=DTYPES[table],
                    chunksize=1000,
                    method="multi",
                )
