"""Build the chain product index from the Kaggle "Time Series UK Supermarket Data" set.

Source: https://www.kaggle.com/datasets/declanmcalinden/time-series-uk-supermarket-data
Licence: Apache 2.0 (as stated by the uploader). Online prices scraped by the uploader,
9 Jan to 13 Apr 2024. We use it to know which exact products each chain sells, so a shelf label
("TSC SS MLK 4PT") can be matched to a real product. Its prices are 2024 online prices: shown
only as dated starting prices until a shopper scans the product, never as current.

Run: .venv/bin/python scripts/fetch_kaggle.py
Downloads about 800 MB to ~/.cache/kagglehub (not the repo) and writes
data/kaggle/products.csv.gz: one row per (chain, product), latest price seen.
"""

import csv
import gzip
import json
from datetime import date
from pathlib import Path

import kagglehub

DATASET = "declanmcalinden/time-series-uk-supermarket-data"
FILES = {"All_Data_ASDA.csv": "Asda", "All_Data_Aldi.csv": "Aldi", "All_Data_Morrisons.csv": "Morrisons",
         "All_Data_Sains.csv": "Sainsbury's", "All_Data_Tesco.csv": "Tesco"}
# Groceries and basics a student buys. Health, beauty, home, baby and pet ranges are dropped.
KEEP = {"food_cupboard", "fresh_food", "drinks", "bakery", "frozen", "free-from", "household"}
OUT = Path(__file__).resolve().parent.parent / "data" / "kaggle"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, counts = {}, {}
    for fname, chain in FILES.items():
        path = Path(kagglehub.dataset_download(DATASET, path=fname))
        with path.open(newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                if r["category"] not in KEEP or not r["names"].strip():
                    continue
                try:
                    price = float(r["prices_(£)"])
                except ValueError:
                    continue
                key, seen = (chain, r["names"].strip()), f"{r['date'][:4]}-{r['date'][4:6]}-{r['date'][6:8]}"
                if key in rows and rows[key]["seen_on"] >= seen:
                    continue
                unit_price = r["prices_unit_(£)"]
                rows[key] = {"chain": chain, "name": key[1], "price": price,
                             "unit_price": unit_price if unit_price not in ("", "nan") else "",
                             "unit": r["unit"], "category": r["category"],
                             "own_brand": int(r["own_brand"] == "True"), "seen_on": seen}
        counts[chain] = sum(1 for k in rows if k[0] == chain)
        print(f"{chain}: {counts[chain]} grocery products")
    with gzip.open(OUT / "products.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["chain", "name", "price", "unit_price", "unit", "category",
                                          "own_brand", "seen_on"])
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: (r["chain"], r["name"])))
    meta = {"source": "Time Series UK Supermarket Data (Kaggle, Declan McAlinden)",
            "url": f"https://www.kaggle.com/datasets/{DATASET}", "licence": "Apache 2.0",
            "prices_from": min(r["seen_on"] for r in rows.values()),
            "prices_to": max(r["seen_on"] for r in rows.values()),
            "fetched_at": date.today().isoformat(), "categories": sorted(KEEP), "products": counts}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
