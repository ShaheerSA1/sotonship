"""Fetch UK prices from Open Food Facts Open Prices (Hugging Face) and map them to our catalogue.

Temporary reference data. Community receipts are the main source; these prices fill gaps
until enough receipts exist. Data (c) Open Food Facts contributors, ODbL.

Steps:
1. Download openfoodfacts/open-prices prices.parquet from Hugging Face. Keep GBP product prices.
2. Look up each barcode on the Open Food Facts product API (name, brand, size, categories,
   allergens, labels). Cached in data/off/products.json so reruns only fetch new barcodes.
3. Map each product to a catalogue id with the rules in MAP below. Unmapped products are kept
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

# catalogue id -> (category tags, any one is enough; brand regex; size regex or None)
# Own-label products are judged on the brands field alone, so "Twinings Everyday" is not own label.
OWN = r"tesco|sainsbury|asda|lidl|aldi|morrisons|co-?op|m&s|marks|iceland|everyday|just essentials|" \
      r"hearty food|stockwell|by sainsbury|nature's pick|milbona|crownfield|baresa|specially selected|" \
      r"deluxe|savers|cucina|harvest morn|snackrite|dairyfine|cowbelle|alesto|freshona|four seasons|" \
      r"ocean rise|the fishmonger|millville|grower's harvest|bramwells|newgate|chef select|vitasia|" \
      r"tower gate|corale|kania|w5|cien|nightingale|simply|smart price|honest value"
MAP = {
    "bananas-5pk-own": (["en:bananas"], OWN, None),
    "apples-6pk-own": (["en:apples"], OWN, r"\b6\b"),
    "onions-1kg-own": (["en:onions"], OWN, r"1\s?kg"),
    "carrots-1kg-own": (["en:carrots"], OWN, r"1\s?kg"),
    "potatoes-2.5kg-own": (["en:potatoes"], OWN, r"2[.,]5\s?kg"),
    "tomatoes-chopped-400g-own": (["en:chopped-tomatoes"], OWN, r"400\s?g"),
    "milk-semi-4pt-own": (["en:semi-skimmed-milks", "en:semi-skimmed-pasteurised-milk"], OWN, r"2[.,]27|4\s?p(in)?ts?\b|2272"),
    "eggs-free-range-6-own": (["en:eggs"], OWN, r"\b6\b"),
    "butter-salted-250g-own": (["en:salted-butters"], OWN, r"250\s?g"),
    "butter-anchor-250g": (["en:butters"], r"anchor", r"250\s?g"),
    "cheddar-mature-400g-own": (["en:cheddar-cheese"], OWN, r"400\s?g"),
    "cheddar-cathedral-350g": (["en:cheddar-cheese"], r"cathedral", r"350\s?g"),
    "yoghurt-greek-500g-own": (["en:greek-style-yogurts"], OWN, r"500\s?g"),
    "bread-white-800g-own": (["en:white-breads"], OWN, r"800\s?g"),
    "bread-warburtons-toastie-800g": (["en:breads"], r"warburtons", r"800\s?g"),
    "chicken-breast-600g-own": (["en:chicken-breasts"], OWN, r"6[05]0\s?g"),
    "beef-mince-5pc-500g-own": (["en:minced-beef-steak-with-5-fat", "en:minced-beef"], OWN, r"500\s?g"),
    "tuna-chunks-brine-145g-own": (["en:tunas"], OWN, r"1[0-4][0-9]\s?g"),
    "pasta-penne-500g-own": (["en:pastas"], OWN, r"500\s?g"),
    "rice-basmati-1kg-own": (["en:basmati-rices"], OWN, r"1\s?kg"),
    "rice-tilda-basmati-1kg": (["en:basmati-rices"], r"tilda", r"1\s?kg"),
    "beans-heinz-415g": (["en:baked-beans-in-tomato-sauce"], r"heinz", r"41[05]\s?g"),
    "beans-own-410g": (["en:baked-beans-in-tomato-sauce"], OWN, r"4[01][05]\s?g"),
    "oats-porridge-1kg-own": (["en:rolled-oats"], OWN, r"1\s?kg"),
    "oats-quaker-1kg": (["en:rolled-oats"], r"quaker", r"1\s?kg"),
    "cornflakes-kelloggs-500g": (["en:corn-flakes"], r"kellogg", r"4[5-9]0\s?g|500\s?g"),
    "cornflakes-own-500g": (["en:corn-flakes"], OWN, r"500\s?g"),
    "noodles-super-chicken-90g": (["en:instant-noodles"], r"batchelors|super ?noodles", r"9[05]\s?g"),
    "pizza-margherita-frozen-own": (["en:frozen-pizzas"], OWN, None),
    "peas-frozen-1kg-own": (["en:frozen-peas"], OWN, r"1\s?kg"),
    "crisps-walkers-sv-6pk": (["en:salt-and-vinegar-crisps", "en:crisps"], r"walkers", r"6\s?x|6 ?pack"),
    "crisps-own-sv-6pk": (["en:salt-and-vinegar-crisps", "en:crisps"], OWN, r"6\s?x|6 ?pack"),
    "crisps-walkers-co-6pk": (["en:cheese-and-onion-crisps"], r"walkers", r"6\s?x|6 ?pack"),
    "crisps-own-co-6pk": (["en:cheese-and-onion-crisps"], OWN, r"6\s?x|6 ?pack"),
    "choc-dairy-milk-110g": (["en:milk-chocolates"], r"cadbury", r"1[01][0-9]\s?g"),
    "cola-coke-2l": (["en:colas"], r"coca|coke", r"2\s?l"),
    "cola-own-2l": (["en:colas"], OWN, r"2\s?l"),
    "oj-smooth-1l-own": (["en:orange-juices"], OWN, r"1\s?l"),
    "tea-pg-80": (["en:black-teas"], r"pg tips", r"\b80\b"),
    "tea-yorkshire-80": (["en:black-teas"], r"yorkshire", r"\b80\b"),
    "tea-own-80": (["en:black-teas"], OWN, r"\b80\b"),
    "coffee-nescafe-gold-200g": (["en:instant-coffees"], r"nescaf", r"200\s?g"),
    "sugar-granulated-1kg-own": (["en:granulated-sugars"], OWN, r"1\s?kg"),
    "peanut-butter-smooth-340g-own": (["en:peanut-butters"], OWN, r"3[0-9]0\s?g"),
    "washing-up-fairy-383ml": (["en:dishwashing-liquids"], r"fairy", r"38[0-9]\s?ml"),
}
# crisps flavour is not a category tag; check the name instead
NAME_RULES = {
    "crisps-walkers-sv-6pk": r"salt.*vinegar|s/vin|s&v",
    "crisps-own-sv-6pk": r"salt.*vinegar|s/vin|s&v",
    "pizza-margherita-frozen-own": r"margh|cheese",
    "tuna-chunks-brine-145g-own": r"brine",
    "pasta-penne-500g-own": r"penne",
    "noodles-super-chicken-90g": r"chicken",
    "beef-mince-5pc-500g-own": r"\b5\s?%|beef mince$|^beef mince",
    "crisps-walkers-co-6pk": r"cheese.*onion",
    "crisps-own-co-6pk": r"cheese.*onion",
}


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


def map_product(p: dict) -> str | None:
    tags = set(p.get("categories_tags") or [])
    brand = (p.get("brands") or "").lower()
    name = (p.get("product_name") or "").lower()
    size = (p.get("quantity") or "").lower() + " " + name
    for pid, (need, brand_rx, size_rx) in MAP.items():
        if not set(need) & tags:
            continue
        where = brand if brand_rx == OWN else brand + " " + name
        if not re.search(brand_rx, where):
            continue
        if size_rx and not re.search(size_rx, size):
            continue
        if pid in NAME_RULES and not re.search(NAME_RULES[pid], name):
            continue
        return pid
    return None


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
