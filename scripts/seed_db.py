"""Rebuild data/app.db with SYNTHETIC receipts so the planner has something to plan with.

Every row written here has synthetic = 1 and the UI labels it. Real receipts uploaded
through the app are kept apart (synthetic = 0). Prices are invented: a base price per
product times a per-chain factor, with noise. They are not real shop prices.

Run: .venv/bin/python scripts/seed_db.py  (deletes and rebuilds data/app.db)
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db  # noqa: E402

# Invented base prices in GBP. Synthetic, not collected from any shop.
BASE = {
    "bananas-5pk-own": 0.85, "apples-6pk-own": 1.60, "onions-1kg-own": 0.95, "carrots-1kg-own": 0.60,
    "potatoes-2.5kg-own": 1.75, "tomatoes-chopped-400g-own": 0.49, "milk-semi-4pt-own": 1.55,
    "eggs-free-range-6-own": 1.75, "butter-salted-250g-own": 2.05, "butter-anchor-250g": 2.65,
    "cheddar-mature-400g-own": 3.35, "cheddar-cathedral-350g": 4.10, "yoghurt-greek-500g-own": 1.25,
    "bread-white-800g-own": 0.75, "bread-warburtons-toastie-800g": 1.55, "chicken-breast-600g-own": 4.40,
    "beef-mince-5pc-500g-own": 3.80, "tuna-chunks-brine-145g-own": 0.95, "pasta-penne-500g-own": 0.75,
    "rice-basmati-1kg-own": 2.20, "rice-tilda-basmati-1kg": 4.25, "beans-heinz-415g": 1.40,
    "beans-own-410g": 0.45, "oats-porridge-1kg-own": 1.05, "oats-quaker-1kg": 2.90,
    "cornflakes-kelloggs-500g": 2.75, "cornflakes-own-500g": 0.95, "noodles-super-chicken-90g": 0.85,
    "pizza-margherita-frozen-own": 1.25, "peas-frozen-1kg-own": 1.30, "crisps-walkers-sv-6pk": 2.10,
    "crisps-own-sv-6pk": 0.95, "crisps-walkers-co-6pk": 2.10, "crisps-own-co-6pk": 0.95,
    "choc-dairy-milk-110g": 1.65, "cola-coke-2l": 2.25, "cola-own-2l": 0.75, "oj-smooth-1l-own": 1.20,
    "tea-pg-80": 2.90, "tea-yorkshire-80": 3.10, "tea-own-80": 1.15, "coffee-nescafe-gold-200g": 7.50,
    "sugar-granulated-1kg-own": 1.10, "peanut-butter-smooth-340g-own": 1.15, "toilet-roll-9-own": 3.75,
    "washing-up-fairy-383ml": 1.50,
}
CHAIN_FACTOR = {"Aldi": 0.88, "Lidl": 0.89, "Asda": 0.95, "Iceland": 0.98, "Tesco": 1.00, "Morrisons": 1.01,
                "Sainsbury's": 1.03, "Co-op": 1.18, "M&S": 1.25}
SMALL_FORMAT = 1.07
LOYALTY_SHARE = {"Tesco": 0.30, "Sainsbury's": 0.25, "Co-op": 0.10, "Lidl": 0.05, "Morrisons": 0.10}


def price(rng: random.Random, product: dict, store: dict) -> float:
    f = CHAIN_FACTOR[store["chain"]]
    if product["brand"] != "own":
        f = 1 + (f - 1) * 0.4  # branded goods vary less between chains
    if store["format"] == "small":
        f *= SMALL_FORMAT
    p = BASE[product["id"]] * f * rng.uniform(0.97, 1.03)
    return round(max(0.25, round(p * 20) / 20 - rng.choice([0, 0, 0.01, 0.05])), 2)


def main() -> None:
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
    conn = db.connect()
    db.init(conn)
    rng = random.Random(42)
    products = db.catalogue(conn)
    stores = db.stores(conn)
    picked = [s for s in stores if s["format"] == "large"] + rng.sample(
        [s for s in stores if s["format"] == "small"], k=12)
    today = date.today()
    n_obs = 0
    for store in picked:
        # Aldi and Lidl carry few big brands
        stock = [p for p in products if p["brand"] == "own" or store["chain"] not in ("Aldi", "Lidl")
                 or rng.random() < 0.35]
        for r in range(rng.randint(1, 3)):
            day = today - timedelta(days=rng.choice([1, 2, 3, 5, 8, 12, 15, 20, 26, 34, 45]))
            cur = conn.execute(
                "INSERT INTO receipts (store_id, purchased_on, source, parser, content_hash, synthetic)"
                " VALUES (?,?,?,?,?,1)", (store["id"], day.isoformat(), "synthetic", "synthetic",
                                          f"synthetic-{store['id']}-{r}"))
            for p in rng.sample(stock, k=min(len(stock), rng.randint(8, 20))):
                unit = price(rng, p, store)
                loyalty = None
                if rng.random() < LOYALTY_SHARE.get(store["chain"], 0):
                    loyalty = round(unit * rng.choice([0.7, 0.75, 0.8, 0.85]), 2)
                conn.execute(
                    """INSERT INTO observations (receipt_id, store_id, product_id, raw_line, quantity, unit_price,
                       loyalty_price, loyalty_scheme, observed_on, confidence, outlier, synthetic)
                       VALUES (?,?,?,?,?,?,?,?,?,?,0,1)""",
                    (cur.lastrowid, store["id"], p["id"], f"[synthetic] {p['name']}", 1, unit, loyalty,
                     db.LOYALTY_SCHEMES.get(store["chain"]) if loyalty else None, day.isoformat(), "high"))
                n_obs += 1
    conn.commit()
    print(f"Synthetic seed: {len(picked)} stores, {n_obs} observations -> {db.DB_PATH}")
    print(db.stats(conn))


if __name__ == "__main__":
    main()
