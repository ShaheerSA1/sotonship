# Data licences

Every file in `data/` and the licence it is under. Full log with dates: `docs/data-sources.md`.

| File | Source | Licence | Notes |
|---|---|---|---|
| `stores.json` | OpenStreetMap, via the Overpass API (`scripts/fetch_stores.py`), OSM data as of 16 Oct 2026 | ODbL 1.0 | Attribution: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright. Filtered to supermarket chains in Southampton. A derivative database, so it stays ODbL. |
| `streets/` | OpenStreetMap, via the Overpass API (`scripts/fetch_streets.py`), OSM data as of 17 Oct 2026 | ODbL 1.0 | Attribution: © OpenStreetMap contributors. Southampton walk, cycle and road networks for routing. A derivative database, so it stays ODbL. |
| `off/` | Open Food Facts | ODbL 1.0, DbCL 1.0, photos CC BY-SA 3.0 | See `off/NOTICE.md`. |
| `kaggle/` | Time Series UK Supermarket Data, Kaggle | Apache 2.0, as stated by the uploader | See `kaggle/NOTICE.md`. Scraped from supermarket websites. |
| `catalogue.json` | Written by the team | Ours | Product names are plain descriptions ("Heinz Baked Beans 415g"). |
| `eval/class_match_*.json` | Open Food Facts products, labels by us | ODbL 1.0 (products) | Derived from `off/products.json`, so it stays ODbL. |
| `eval/label_test.json`, `eval/labels/` | Rendered by `scripts/make_labels.py` | Ours, product names from Kaggle (Apache 2.0) | Synthetic. |
| `eval/list_items_test.json` | Written by the team | Ours | Synthetic. |
| `eval/results.json` | Output of `scripts/eval.py` | Ours | |
| `app.db` | Built locally, not in git | Mixed | Holds copies of the above plus shopper prices. Never share it whole: export shopper prices only (see below). |

## Shopper prices

Prices people save in the app (shelf labels and barcode scans) are ours, under the terms shown on the Scan screen. Shoppers agree to share them when they save one. To share or sell price data, export only these columns from `observations`: store, our catalogue class, price, member price, offer fields and date. Leave out `raw_line` on scan rows and any class with origin `scan`, because those names come from Open Food Facts (ODbL). A barcode the shopper scanned is a fact printed on the pack and can stay. Never include Kaggle prices.
