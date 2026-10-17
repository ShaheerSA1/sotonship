"""Fetch UK prices from Open Food Facts Open Prices (Hugging Face) and map them to our catalogue.

Temporary reference data. Shelf prices scanned by shoppers are the main source; these prices fill
gaps until enough scans exist. Data (c) Open Food Facts contributors, ODbL.

Steps:
1. Download openfoodfacts/open-prices prices.parquet from Hugging Face. Keep GBP product prices.
2. Look up each barcode on the Open Food Facts product API (name, brand, size, categories,
   allergens, labels). Cached in data/off/products.json so reruns only fetch new barcodes.
3. Map each product to a catalogue id with the rules in app/offmap.py. Unmapped products are kept
   in the products cache but not written to the price file.
4. Write data/off/prices.json.

Run: .venv/bin/python scripts/fetch_off.py  (about 35 minutes on the first run, the API rate-limits product lookups)
Flags: --no-download reuses data/off/cache/prices.parquet, --no-lookup maps only barcodes already cached.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.offmap import map_product  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OFF = ROOT / "data" / "off"
CACHE = OFF / "cache"  # gitignored: the raw parquet
PARQUET_URL = "https://huggingface.co/datasets/openfoodfacts/open-prices/resolve/main/prices.parquet"
PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{code}"
FIELDS = "code,product_name,brands,quantity,categories_tags,allergens_tags,traces_tags,labels_tags,ingredients_analysis_tags"
HEADERS = {"User-Agent": "Nostobon/0.1 (SotonShip 2026 hackathon, student project)"}

# Chain from the shop name in Open Prices. Same names as data/stores.json.
CHAINS = [
    ("Tesco", r"^tesco"), ("Sainsbury's", r"^sainsbury"), ("Asda", r"^asda"), ("Lidl", r"^lidl"),
    ("Aldi", r"^aldi"), ("Morrisons", r"^morrisons"), ("Co-op", r"co-?op|co-operative"),
    ("M&S", r"^m&s|marks (and|&) spencer"), ("Iceland", r"^iceland"),
]
SMALL = re.compile(r"express|local|daily|simply food|metro|food to go", re.I)


def chain_of(name: str) -> tuple[str | None, str]:
    n = (name or "").strip().lower()
    for chain, rx in CHAINS:
        if re.search(rx, n):
            return chain, "small" if SMALL.search(n) else "large"
    return None, "large"


def download_parquet() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "prices.parquet"
    print("Downloading", PARQUET_URL)
    with httpx.stream("GET", PARQUET_URL, follow_redirects=True, timeout=300, headers=HEADERS) as r:
        r.raise_for_status()
        with path.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return path


def lookup(codes: list[str]) -> dict:
    path = OFF / "products.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    todo = [c for c in codes if c not in cache]
    print(f"{len(codes)} barcodes, {len(todo)} to look up", flush=True)
    with httpx.Client(headers=HEADERS, timeout=20) as client:
        for i, code in enumerate(todo):
            for _ in range(5):
                try:
                    r = client.get(PRODUCT_URL.format(code=code), params={"fields": FIELDS})
                except httpx.HTTPError:
                    time.sleep(5)
                    continue
                if r.status_code == 429:  # the API's per-minute limit: wait it out
                    time.sleep(60)
                    continue
                if r.status_code >= 500:
                    time.sleep(10)
                    continue
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                cache[code] = body.get("product") if body.get("status") == 1 else None
                break
            time.sleep(1.1)  # about 50 a minute, half the documented limit
            if i % 50 == 49:
                path.write_text(json.dumps(cache, indent=0))
                print(f"  {i + 1}/{len(todo)}", flush=True)
    path.write_text(json.dumps(cache, indent=0))
    return cache


def main() -> None:
    OFF.mkdir(parents=True, exist_ok=True)
    parquet = CACHE / "prices.parquet"
    if "--no-download" not in sys.argv or not parquet.exists():
        parquet = download_parquet()
    table = pq.read_table(parquet)
    rows = table.filter(pc.and_(pc.equal(table["currency"], "GBP"), pc.equal(table["type"], "PRODUCT"))).to_pylist()
    codes = sorted({r["product_code"] for r in rows if r["product_code"]})
    if "--no-lookup" in sys.argv:  # map with whatever is cached
        path = OFF / "products.json"
        products = json.loads(path.read_text()) if path.exists() else {}
    else:
        products = lookup(codes)

    out, unmapped_chain = [], 0
    for r in rows:
        p = products.get(r["product_code"])
        pid = map_product(p) if p else None
        if not pid:
            continue
        chain, fmt = chain_of(r["location_osm_display_name"] or "")
        if not chain:
            unmapped_chain += 1
            continue
        if r["price_per"] not in (None, "UNIT"):
            continue
        price = float(r["price"])
        regular = float(r["price_without_discount"]) if r["price_without_discount"] else price
        loyalty = price if r["price_is_discounted"] and r["discount_type"] == "LOYALTY_PROGRAM" else None
        # other promotions end, so the planner uses the regular price
        out.append({
            "off_price_id": r["id"], "product_id": pid, "barcode": r["product_code"],
            "off_name": p.get("product_name"), "off_brand": p.get("brands"), "off_quantity": p.get("quantity"),
            "chain": chain, "format": fmt, "location": (r["location_osm_display_name"] or "").split(",")[0].strip(),
            "city": r["location_osm_address_city"], "unit_price": regular, "loyalty_price": loyalty,
            "promo_price": price if r["price_is_discounted"] and loyalty is None else None,
            "observed_on": r["date"].isoformat(), "proof_type": r["proof_type"],
            "allergens": p.get("allergens_tags") or [], "traces": p.get("traces_tags") or [],
            "labels": p.get("labels_tags") or [], "analysis": p.get("ingredients_analysis_tags") or [],
        })
    result = {
        "source": "Open Food Facts Open Prices, via Hugging Face (openfoodfacts/open-prices)",
        "url": "https://huggingface.co/datasets/openfoodfacts/open-prices",
        "licence": "ODbL 1.0, Open Food Facts contributors",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gbp_product_prices": len(rows), "barcodes": len(codes), "mapped_prices": len(out),
        "prices": out,
    }
    (OFF / "prices.json").write_text(json.dumps(result, indent=1))
    print(f"{len(rows)} GBP prices, {len(out)} mapped to the catalogue, {unmapped_chain} at shops we do not track")


if __name__ == "__main__":
    main()
