"""Barcode scan: barcode to product (Open Food Facts), own-label check.

No AI here. Barcode checks and own-label detection are rules. Which class the product is
compared in is decided in app/classes.py.
Lookups are cached in SQLite. If Open Food Facts cannot be reached, the committed
cache in data/off/products.json is used and the answer says so.
"""

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import httpx

from . import db

PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{code}"
PRODUCT_PAGE = "https://world.openfoodfacts.org/product/{code}"
FIELDS = ("code,product_name,product_name_en,brands,quantity,categories_tags,allergens_tags,traces_tags,"
          "labels_tags,ingredients_analysis_tags,image_front_small_url,image_front_url")
HEADERS = {"User-Agent": "Nostobon/0.1 (SotonShip 2026 hackathon, student project)"}
TIMEOUT = 6.0
RETRY_MISSING = timedelta(days=1)  # products get added to Open Food Facts all the time
COMMITTED_CACHE_DATE = "2026-10-17"  # when scripts/fetch_off.py filled data/off/products.json

# Brand names each chain uses for its own label. Lower case, matched against the brands field.
OWN_LABEL = {
    "Tesco": r"tesco|stockwell|hearty food|creamfields|ms molly|eastman|boswell farms|willow farm|woodside farms|"
             r"redmere farms|rosedene farms|nightingale farms|suntrail farms|grower's harvest",
    "Sainsbury's": r"sainsbury|taste the difference|stamford street|hubbard",
    "Asda": r"asda|just essentials|extra special|smart price",
    "Lidl": r"lidl|milbona|crownfield|baresa|freshona|combino|deluxe|snack day|alesto|solevita|pilos|cien|"
            r"\bw5\b|chef select|vitasia|kania|dulano|rowan hill|mcennedy|tower gate|harvest basket|oaklands|"
            r"birchwood|newgate",
    "Aldi": r"aldi|specially selected|everyday essentials|cowbelle|dairyfine|harvest morn|snackrite|"
            r"nature's pick|ashfield farm|brooklea|four seasons|the fishmonger|bramwells|ocean rise|emporium|"
            r"crestwood|colway|corale|millfield|holly lane|the pantry|village bakery|grower's selection",
    "Morrisons": r"morrisons|\bsavers\b|the best|market street",
    "Co-op": r"co-?op|irresistible|honest value",
    "M&S": r"m&s|marks (and|&) spencer",
    "Iceland": r"iceland",
}


# Own label comes in three tiers, priced as different products: value (the "off brand" ranges), standard, and
# premium. Matched against the brand field or a product name. Anything own label that matches neither is standard.
VALUE_LABEL = (r"stockwell|hearty food|creamfields|ms molly|eastman|grower's harvest|stamford street|hubbard|"
               r"just essentials|smart price|everyday essentials|\bsavers\b|honest value|\bbasics\b")
PREMIUM_LABEL = (r"finest|taste the difference|extra special|specially selected|\bthe best\b|\bdeluxe\b|"
                 r"irresistible|m&s collection")


def own_label_tier(text: str) -> str:
    """"value", "premium" or "own" (standard) for a product already known to be own label."""
    t = (text or "").lower()
    if re.search(VALUE_LABEL, t):
        return "value"
    if re.search(PREMIUM_LABEL, t):
        return "premium"
    return "own"


class LookupFailed(Exception):
    pass


def clean(code: str) -> str:
    return re.sub(r"\D", "", code or "")


def check_digit_ok(code: str) -> bool:
    """GS1 check digit, valid for EAN-8, UPC-A, EAN-13 and GTIN-14."""
    body, check = code[:-1], int(code[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def normalise(raw: str) -> tuple[str | None, str | None]:
    """(code, problem). UPC-A becomes EAN-13, as Open Food Facts stores it."""
    code = clean(raw)
    if len(code) not in (8, 12, 13, 14):
        return None, f"A barcode has 8, 12, 13 or 14 digits. This has {len(code)}."
    if not check_digit_ok(code):
        return None, "The last digit does not fit the rest, so a digit is misread. Scan or type it again."
    if len(code) == 12:
        code = "0" + code
    if len(code) == 14 and code.startswith("0"):
        code = code[1:]
    return code, None


def in_store_code(code: str) -> bool:
    """Prefix 2 is for codes a shop assigns itself: weighed items, deli counters, some own label."""
    return code[0] == "2" if len(code) in (8, 13) else False


def own_label_chain(product: dict) -> str | None:
    brand = (product.get("brands") or "").lower()
    if not brand:
        return None
    for chain, rx in OWN_LABEL.items():
        if re.search(rx, brand):
            return chain
    return None


def _fetch(code: str) -> dict | None:
    try:
        r = httpx.get(PRODUCT_URL.format(code=code), params={"fields": FIELDS}, headers=HEADERS, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise LookupFailed(f"Open Food Facts did not answer ({type(e).__name__}).")
    if r.status_code == 404:
        return None
    if r.status_code == 429:
        raise LookupFailed("Open Food Facts is rate-limiting us. Try again in a minute.")
    if r.status_code >= 400:
        raise LookupFailed(f"Open Food Facts returned HTTP {r.status_code}.")
    body = r.json()
    return body.get("product") if body.get("status") == 1 else None


def _committed_cache(code: str) -> tuple[bool, dict | None]:
    path = db.DATA / "off" / "products.json"
    if not path.exists():
        return False, None
    cache = json.loads(path.read_text())
    return code in cache, cache.get(code)


def lookup(conn: sqlite3.Connection, code: str) -> tuple[dict | None, dict]:
    """(product or None, provenance). Provenance says live or cached, and when fetched."""
    row = conn.execute("SELECT product, fetched_at FROM off_products WHERE barcode = ?", (code,)).fetchone()
    now = datetime.now(timezone.utc)
    if row and (row["product"] or now - datetime.fromisoformat(row["fetched_at"]) < RETRY_MISSING):
        return (json.loads(row["product"]) if row["product"] else None), {"live": False, "fetched_at": row["fetched_at"]}
    try:
        product = _fetch(code)
    except LookupFailed as e:
        known, product = _committed_cache(code)
        if known:
            return product, {"live": False, "fetched_at": COMMITTED_CACHE_DATE,
                             "note": f"{e} Using our copy from {COMMITTED_CACHE_DATE}."}
        raise
    fetched = now.isoformat(timespec="seconds")
    conn.execute("INSERT OR REPLACE INTO off_products (barcode, product, fetched_at) VALUES (?,?,?)",
                 (code, json.dumps(product) if product else None, fetched))
    conn.commit()
    return product, {"live": True, "fetched_at": fetched}


def describe(conn: sqlite3.Connection, raw: str) -> dict:
    """Everything the scan screen needs for one barcode. Never raises for a bad code: it says what is wrong."""
    code, problem = normalise(raw)
    if problem:
        return {"code": clean(raw), "status": "invalid", "note": problem}
    out = {"code": code, "in_store_code": in_store_code(code)}
    try:
        product, source = lookup(conn, code)
    except LookupFailed as e:
        return {**out, "status": "unavailable", "note": f"{e} Type the product name instead."}
    out["source"] = {**source, "name": "Open Food Facts", "licence": "ODbL", "url": PRODUCT_PAGE.format(code=code)}
    if not product or not (product.get("product_name_en") or product.get("product_name")):
        note = ("This is a code the shop prints itself (weighed, deli or bakery items). It does not identify the "
                "product. Type what it is." if out["in_store_code"] else
                "Open Food Facts does not know this barcode yet. Type the name, size and brand from the pack.")
        return {**out, "status": "not_found", "note": note}
    return {
        **out, "status": "found",
        "name": product.get("product_name_en") or product.get("product_name"),
        "brand": product.get("brands") or None,
        "quantity": product.get("quantity") or None,
        "image_url": product.get("image_front_small_url") or product.get("image_front_url"),
        "own_label_of": own_label_chain(product),
        "_product": product,  # for app/classes.py, removed before it reaches the browser
    }


def cached_own_label(conn: sqlite3.Connection, code: str) -> str | None:
    row = conn.execute("SELECT product FROM off_products WHERE barcode = ?", (code,)).fetchone()
    return own_label_chain(json.loads(row["product"])) if row and row["product"] else None


def median_for_barcode(conn: sqlite3.Connection, code: str) -> float | None:
    rows = [r[0] for r in conn.execute(
        "SELECT unit_price FROM observations WHERE barcode = ? AND outlier = 0 ORDER BY unit_price", (code,))]
    return rows[len(rows) // 2] if len(rows) >= 3 else None
