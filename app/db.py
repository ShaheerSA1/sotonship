"""SQLite store for stores, products and the shelf prices shoppers scan."""

import csv
import gzip
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB_PATH = Path(os.environ.get("NOSTOBON_DB") or DATA / "app.db")  # override for tests


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
-- Product classes. The catalogue seeds them; scans that fit no class add more (origin 'scan').
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY, name TEXT, generic TEXT, brand TEXT, size TEXT,
    origin TEXT DEFAULT 'catalogue', created_on TEXT
);
-- One shelf price a shopper saved, from a shelf label photo or a barcode scan.
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT REFERENCES stores(id),
    product_id TEXT REFERENCES products(id),  -- product class; NULL when not matched to one yet
    raw_line TEXT,              -- product name as on the label or from Open Food Facts
    quantity REAL,
    unit_price REAL,            -- shelf price for one unit
    loyalty_price REAL,         -- member price on the label, if there is one
    loyalty_scheme TEXT,
    observed_on TEXT,
    confidence TEXT,
    outlier INTEGER DEFAULT 0,  -- far from other prices for this product, not used in plans
    synthetic INTEGER DEFAULT 0,
    chain_product_id INTEGER,   -- exact product in the chain's list (Kaggle index)
    identified_by TEXT,         -- ai | baseline | shopper | barcode | device
    barcode TEXT,
    method TEXT,                -- label | scan | trip (a price corrected after a shop)
    valid_until TEXT,           -- last day of the offer, YYYY-MM-DD
    was_price REAL,             -- price before the offer, if printed
    multibuy_qty INTEGER,       -- "3 for £5": 3
    multibuy_price REAL,        -- "3 for £5": 5.00
    multibuy_scheme TEXT        -- set when only members get the multibuy
);
CREATE INDEX IF NOT EXISTS obs_product_store ON observations(product_id, store_id, observed_on);
-- Open Food Facts Open Prices, mapped to the catalogue by scripts/fetch_off.py. Temporary fallback:
-- chain-level prices from anywhere in the UK, used only where no shopper price covers a shop.
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
-- Exact products each chain sells, from the Kaggle set (scripts/fetch_kaggle.py). Prices are 2024
-- online prices: the starting price for a product at a chain until a shopper scans it, always
-- shown with its date. Also the list a shelf label is matched against.
CREATE TABLE IF NOT EXISTS chain_products (
    id INTEGER PRIMARY KEY, chain TEXT, name TEXT, price REAL, unit_price REAL, unit TEXT,
    category TEXT, own_brand INTEGER, seen_on TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS chain_products_fts USING fts5(name, content='chain_products', content_rowid='id',
                                                              tokenize='porter unicode61');
-- Which Kaggle product is each product class at each chain (scripts/link_classes.py). This is how a
-- class gets its starting price everywhere, and how a shelf label matched to a Kaggle product joins a class.
CREATE TABLE IF NOT EXISTS class_links (
    class_id TEXT REFERENCES products(id), chain TEXT,
    chain_product_id INTEGER REFERENCES chain_products(id),
    by TEXT,                    -- ai | rules | team | scan (made when a shelf label was saved, app/classes.py)
    reason TEXT,
    PRIMARY KEY (class_id, chain)
);
-- Open Food Facts answers for scanned barcodes. product is NULL when the barcode is unknown.
CREATE TABLE IF NOT EXISTS off_products (
    barcode TEXT PRIMARY KEY, product TEXT, fetched_at TEXT
);
-- Which product class a scanned barcode belongs to, as saved by a shopper (app/classes.py).
-- class_id NULL: the shopper said it is not the product we suggested.
CREATE TABLE IF NOT EXISTS class_members (
    barcode TEXT PRIMARY KEY, class_id TEXT REFERENCES products(id),
    name TEXT, brand TEXT, quantity TEXT, category TEXT, own_label_of TEXT,
    by TEXT,                    -- ai | rules | shopper: who chose the class the shopper accepted
    added_on TEXT
);
-- AI answers per barcode, so the same product is not sent twice.
CREATE TABLE IF NOT EXISTS class_guesses (
    barcode TEXT PRIMARY KEY, result TEXT, made_at TEXT
);
-- Households share one shopping list (app/household.py). No accounts: a member is a nickname and a
-- random token kept on their device. Anyone with the join code can join, as a member.
CREATE TABLE IF NOT EXISTS households (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,           -- join code, shared by the members
    name TEXT,
    created_on TEXT
);
CREATE TABLE IF NOT EXISTS household_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER REFERENCES households(id),
    name TEXT,                  -- nickname
    role TEXT,                  -- owner: started it, cannot be removed | admin: manages people | member
    token TEXT UNIQUE,          -- secret on the member's device, sent as X-Member-Token
    joined_on TEXT
);
CREATE TABLE IF NOT EXISTS household_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id INTEGER REFERENCES households(id),
    text TEXT,
    status TEXT,                -- listed | bought
    added_by INTEGER,           -- member id; kept after they leave, shown as "someone who left"
    bought_by INTEGER,
    claimed_by INTEGER,         -- member who said they will buy it; lapses after a day (app/household.py)
    claimed_at TEXT,
    updated_at TEXT
);
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
    pcols = {r[1] for r in conn.execute("PRAGMA table_info(products)")}
    if "origin" not in pcols:  # databases created before product classes
        conn.execute("ALTER TABLE products ADD COLUMN origin TEXT DEFAULT 'catalogue'")  # catalogue | scan
        conn.execute("ALTER TABLE products ADD COLUMN created_on TEXT")
    products = json.loads((DATA / "catalogue.json").read_text())["products"]
    conn.executemany(
        "INSERT OR REPLACE INTO products (id, name, generic, brand, size) VALUES (:id, :name, :generic, :brand, :size)",
        products)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(observations)")}
    if "chain_product_id" not in cols:  # databases created before exact product matching
        conn.execute("ALTER TABLE observations ADD COLUMN chain_product_id INTEGER")
        conn.execute("ALTER TABLE observations ADD COLUMN identified_by TEXT")
    if "barcode" not in cols:  # databases created before barcode scanning
        conn.execute("ALTER TABLE observations ADD COLUMN barcode TEXT")
        conn.execute("ALTER TABLE observations ADD COLUMN method TEXT")  # label | scan | trip
    # added with shelf labels: the offer printed on the label
    for col, kind in (("valid_until", "TEXT"),       # last day of the offer, YYYY-MM-DD
                      ("was_price", "REAL"),         # price before the offer, if printed
                      ("multibuy_qty", "INTEGER"),   # "3 for £5": 3
                      ("multibuy_price", "REAL"),    # "3 for £5": 5.00
                      ("multibuy_scheme", "TEXT")):  # set when only members get the multibuy
        if col not in cols:
            conn.execute(f"ALTER TABLE observations ADD COLUMN {col} {kind}")
    # households before owner and admin roles: adults become admins, children members, the first admin owns it
    conn.execute("UPDATE household_members SET role = CASE role WHEN 'adult' THEN 'admin' ELSE 'member' END "
                 "WHERE role IN ('adult', 'child')")
    conn.execute("""UPDATE household_members SET role = 'owner' WHERE id IN (
                        SELECT (SELECT id FROM household_members m WHERE m.household_id = h.household_id
                                ORDER BY m.role = 'admin' DESC, m.id LIMIT 1)
                        FROM household_members h GROUP BY h.household_id HAVING SUM(h.role = 'owner') = 0)""")
    conn.execute("UPDATE household_items SET status = 'listed' WHERE status = 'requested'")
    conn.execute("DELETE FROM household_items WHERE status = 'rejected'")
    hcols = {r[1] for r in conn.execute("PRAGMA table_info(household_items)")}
    if "claimed_by" not in hcols:  # households before "who is getting this"
        conn.execute("ALTER TABLE household_items ADD COLUMN claimed_by INTEGER")
        conn.execute("ALTER TABLE household_items ADD COLUMN claimed_at TEXT")
    load_reference(conn)
    load_chain_products(conn)
    load_class_links(conn)
    # label prices saved before their product had a class join it once it has one
    conn.execute("""UPDATE observations SET product_id = (SELECT class_id FROM class_links l
                        WHERE l.chain_product_id = observations.chain_product_id)
                    WHERE product_id IS NULL AND chain_product_id IS NOT NULL""")
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


def load_chain_products(conn: sqlite3.Connection) -> None:
    """Load data/kaggle/products.csv.gz once. Skipped when the table already matches the file."""
    path, meta = DATA / "kaggle" / "products.csv.gz", kaggle_meta()
    if not path.exists() or not meta:
        return
    have = conn.execute("SELECT COUNT(*) FROM chain_products").fetchone()[0]
    if have == sum(meta["products"].values()):
        return
    # ids change on a rebuild, and links hold them. load_class_links reloads the file's links after this;
    # links made by label scans are found again here by chain and name.
    scan_links = conn.execute("""SELECT l.class_id, l.chain, l.reason, cp.name FROM class_links l
                                 JOIN chain_products cp ON cp.id = l.chain_product_id WHERE l.by = 'scan'""").fetchall()
    conn.execute("DELETE FROM class_links")
    conn.execute("DELETE FROM chain_products")
    with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
        conn.executemany(
            """INSERT INTO chain_products (chain, name, price, unit_price, unit, category, own_brand, seen_on)
               VALUES (:chain, :name, :price, NULLIF(:unit_price, ''), :unit, :category, :own_brand, :seen_on)""",
            csv.DictReader(f))
    conn.execute("INSERT INTO chain_products_fts(chain_products_fts) VALUES ('rebuild')")
    for l in scan_links:
        row = conn.execute("SELECT id FROM chain_products WHERE chain = ? AND name = ?", (l["chain"], l["name"])).fetchone()
        if row:
            conn.execute("INSERT OR IGNORE INTO class_links VALUES (?,?,?,'scan',?)",
                         (l["class_id"], l["chain"], row["id"], l["reason"]))


def load_class_links(conn: sqlite3.Connection) -> None:
    """data/kaggle/class_links.json, keyed by product name so a rebuilt chain_products table still lines up.
    Links made by shelf label scans are kept; the file wins where both link a class at the same chain."""
    path = DATA / "kaggle" / "class_links.json"
    if not path.exists():
        return
    conn.execute("DELETE FROM class_links WHERE by != 'scan'")
    for l in json.loads(path.read_text())["links"]:
        row = conn.execute("SELECT id FROM chain_products WHERE chain = ? AND name = ?", (l["chain"], l["name"])).fetchone()
        if row:
            conn.execute("INSERT OR REPLACE INTO class_links VALUES (?,?,?,?,?)",
                         (l["class_id"], l["chain"], row["id"], l["by"], l["reason"]))


def class_for(conn: sqlite3.Connection, chain_product_id: int) -> str | None:
    row = conn.execute("SELECT class_id FROM class_links WHERE chain_product_id = ?", (chain_product_id,)).fetchone()
    return row["class_id"] if row else None


def kaggle_meta() -> dict | None:
    path = DATA / "kaggle" / "meta.json"
    return json.loads(path.read_text()) if path.exists() else None


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


def baseline_prices(conn: sqlite3.Connection, product_ids: list[str]) -> list[dict]:
    """The 2024 online price of each class at each chain it is linked at. No age limit: this is the floor."""
    if not product_ids:
        return []
    marks = ",".join("?" * len(product_ids))
    sql = f"""
    SELECT l.class_id AS product_id, l.chain, l.by AS linked_by, cp.id AS chain_product_id, cp.name AS chain_name,
           cp.price AS unit_price, cp.seen_on AS observed_on,
           CAST(julianday('now') - julianday(cp.seen_on) AS INTEGER) AS age_days
    FROM class_links l JOIN chain_products cp ON cp.id = l.chain_product_id
    WHERE l.class_id IN ({marks})
    """
    return [dict(r) for r in conn.execute(sql, product_ids)]


def stats(conn: sqlite3.Connection) -> dict:
    q = lambda sql: conn.execute(sql).fetchone()[0]
    return {
        "observations": q("SELECT COUNT(*) FROM observations"),
        "observations_real": q("SELECT COUNT(*) FROM observations WHERE synthetic = 0"),
        "scans": q("SELECT COUNT(*) FROM observations WHERE method = 'scan'"),
        "unmatched": q("SELECT COUNT(*) FROM observations WHERE product_id IS NULL"),
        "stores_with_prices": q("SELECT COUNT(DISTINCT store_id) FROM observations"),
        "products": q("SELECT COUNT(*) FROM products"),
        "scan_classes": q("SELECT COUNT(*) FROM products WHERE origin = 'scan'"),
        "latest_observation": q("SELECT MAX(observed_on) FROM observations"),
        "reference_prices": q("SELECT COUNT(*) FROM reference_prices"),
        "reference_products": q("SELECT COUNT(DISTINCT product_id) FROM reference_prices"),
        "latest_reference": q("SELECT MAX(observed_on) FROM reference_prices"),
        "labels": q("SELECT COUNT(*) FROM observations WHERE method = 'label'"),
        "baseline_links": q("SELECT COUNT(*) FROM class_links"),
        "baseline_classes": q("SELECT COUNT(DISTINCT class_id) FROM class_links"),
    }
