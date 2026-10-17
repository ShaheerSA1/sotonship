"""SQLite store for stores, products, receipts and price observations."""

import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB_PATH = DATA / "app.db"


def load_env() -> None:
    """Read .env into os.environ without overriding variables already set."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


load_env()  # before app.ai reads MODEL

SCHEMA = """
CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY, chain TEXT, name TEXT, format TEXT,
    lat REAL, lon REAL, address TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY, name TEXT, generic TEXT, brand TEXT, size TEXT
);
CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT REFERENCES stores(id),
    purchased_on TEXT,          -- date on the receipt
    uploaded_at TEXT DEFAULT (datetime('now')),
    source TEXT,                -- photo | e-receipt | text | synthetic
    parser TEXT,                -- ai | baseline | synthetic
    content_hash TEXT UNIQUE,   -- stops the same receipt being uploaded twice
    synthetic INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER REFERENCES receipts(id),
    store_id TEXT REFERENCES stores(id),
    product_id TEXT REFERENCES products(id),  -- NULL when the line could not be matched
    raw_line TEXT,
    quantity REAL,
    unit_price REAL,            -- shelf price for one unit
    loyalty_price REAL,         -- price with the loyalty scheme, if the receipt shows one
    loyalty_scheme TEXT,
    observed_on TEXT,
    confidence TEXT,
    outlier INTEGER DEFAULT 0,  -- far from other prices for this product, not used in plans
    synthetic INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS obs_product_store ON observations(product_id, store_id, observed_on);
-- Open Food Facts Open Prices, mapped to the catalogue by scripts/fetch_off.py. Temporary fallback:
-- chain-level prices from anywhere in the UK, used only where no community receipt covers a shop.
CREATE TABLE IF NOT EXISTS reference_prices (
    off_price_id INTEGER PRIMARY KEY,
    product_id TEXT REFERENCES products(id),
    chain TEXT, format TEXT,
    location TEXT, city TEXT,
    unit_price REAL, loyalty_price REAL, promo_price REAL,
    observed_on TEXT, proof_type TEXT,
    barcode TEXT, off_name TEXT
);
CREATE INDEX IF NOT EXISTS ref_product_chain ON reference_prices(product_id, chain, observed_on);
"""

LOYALTY_SCHEMES = {
    "Tesco": "Clubcard",
    "Sainsbury's": "Nectar",
    "Lidl": "Lidl Plus",
    "Co-op": "Co-op Membership",
    "Morrisons": "More Card",
    "Asda": "Asda Rewards",
    "M&S": "Sparks",
}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # one shared connection, single-process demo
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    stores = json.loads((DATA / "stores.json").read_text())["stores"]
    conn.executemany(
        "INSERT OR REPLACE INTO stores VALUES (:id, :chain, :name, :format, :lat, :lon, :address)", stores
    )
    products = json.loads((DATA / "catalogue.json").read_text())["products"]
    conn.executemany(
        "INSERT OR REPLACE INTO products VALUES (:id, :name, :generic, :brand, :size)", products
    )
    load_reference(conn)
    conn.commit()


def load_reference(conn: sqlite3.Connection) -> None:
    path = DATA / "off" / "prices.json"
    if not path.exists():
        return
    rows = json.loads(path.read_text())["prices"]
    conn.execute("DELETE FROM reference_prices")
    conn.executemany(
        """INSERT INTO reference_prices VALUES (:off_price_id, :product_id, :chain, :format, :location, :city,
           :unit_price, :loyalty_price, :promo_price, :observed_on, :proof_type, :barcode, :off_name)""", rows)


def reference_meta() -> dict | None:
    path = DATA / "off" / "prices.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    return {k: d[k] for k in ("source", "url", "licence", "fetched_at", "gbp_product_prices", "mapped_prices")}


def catalogue(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM products ORDER BY generic, brand")]


def stores(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM stores ORDER BY chain, name")]


def store(conn: sqlite3.Connection, store_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    return dict(row) if row else None


def median_price(conn: sqlite3.Connection, product_id: str) -> float | None:
    rows = [r[0] for r in conn.execute(
        "SELECT unit_price FROM observations WHERE product_id = ? AND outlier = 0 ORDER BY unit_price",
        (product_id,),
    )]
    if len(rows) < 3:
        return None
    return rows[len(rows) // 2]


def latest_prices(conn: sqlite3.Connection, product_ids: list[str], max_age_days: int) -> list[dict]:
    """Latest non-outlier observation per (product, store), within max_age_days."""
    if not product_ids:
        return []
    marks = ",".join("?" * len(product_ids))
    sql = f"""
    SELECT o.*, s.chain, s.format, s.name AS store_name,
           CAST(julianday('now') - julianday(o.observed_on) AS INTEGER) AS age_days,
           (SELECT COUNT(*) FROM observations o2
             WHERE o2.product_id = o.product_id AND o2.store_id = o.store_id AND o2.outlier = 0) AS n_obs
    FROM observations o JOIN stores s ON s.id = o.store_id
    WHERE o.product_id IN ({marks}) AND o.outlier = 0
      AND julianday('now') - julianday(o.observed_on) <= ?
      AND o.id = (SELECT o3.id FROM observations o3
                  WHERE o3.product_id = o.product_id AND o3.store_id = o.store_id AND o3.outlier = 0
                  ORDER BY o3.observed_on DESC, o3.id DESC LIMIT 1)
    """
    return [dict(r) for r in conn.execute(sql, (*product_ids, max_age_days))]


def reference_prices(conn: sqlite3.Connection, product_ids: list[str], max_age_days: int) -> list[dict]:
    """Latest Open Food Facts price per (product, chain, format), within max_age_days."""
    if not product_ids:
        return []
    marks = ",".join("?" * len(product_ids))
    sql = f"""
    SELECT r.*, CAST(julianday('now') - julianday(r.observed_on) AS INTEGER) AS age_days,
           (SELECT COUNT(*) FROM reference_prices r2
             WHERE r2.product_id = r.product_id AND r2.chain = r.chain) AS n_obs
    FROM reference_prices r
    WHERE r.product_id IN ({marks}) AND julianday('now') - julianday(r.observed_on) <= ?
      AND r.off_price_id = (SELECT r3.off_price_id FROM reference_prices r3
                            WHERE r3.product_id = r.product_id AND r3.chain = r.chain AND r3.format = r.format
                            ORDER BY r3.observed_on DESC, r3.off_price_id DESC LIMIT 1)
    """
    return [dict(r) for r in conn.execute(sql, (*product_ids, max_age_days))]


def stats(conn: sqlite3.Connection) -> dict:
    q = lambda sql: conn.execute(sql).fetchone()[0]
    return {
        "receipts": q("SELECT COUNT(*) FROM receipts"),
        "receipts_real": q("SELECT COUNT(*) FROM receipts WHERE synthetic = 0"),
        "observations": q("SELECT COUNT(*) FROM observations"),
        "observations_real": q("SELECT COUNT(*) FROM observations WHERE synthetic = 0"),
        "unmatched_lines": q("SELECT COUNT(*) FROM observations WHERE product_id IS NULL"),
        "stores_with_prices": q("SELECT COUNT(DISTINCT store_id) FROM observations"),
        "products": q("SELECT COUNT(*) FROM products"),
        "latest_observation": q("SELECT MAX(observed_on) FROM observations"),
        "reference_prices": q("SELECT COUNT(*) FROM reference_prices"),
        "reference_products": q("SELECT COUNT(DISTINCT product_id) FROM reference_prices"),
        "latest_reference": q("SELECT MAX(observed_on) FROM reference_prices"),
    }
