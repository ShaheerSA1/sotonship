# Data sources

Licence notes per file: `data/NOTICE.md`, `data/off/NOTICE.md`, `data/kaggle/NOTICE.md`.

Every source the product uses. The README must list these with date and licence, so log them here as you add them.

| Source | URL | What we use it for | Licence / terms | Date collected | Live, cached or synthetic |
|---|---|---|---|---|---|
| OpenStreetMap shops, Southampton (`data/stores.json`) | https://overpass-api.de/api/interpreter, query in `scripts/fetch_stores.py` | Shop names, chains, locations, addresses. 62 chain shops kept of 235 | ODbL 1.0, credit OpenStreetMap contributors | 16 Oct 2026 (OSM base 22:56 UTC) | Cached |
| Open Food Facts Open Prices (`data/off/prices.json`) | https://huggingface.co/datasets/openfoodfacts/open-prices (prices.parquet) | UK (GBP) product prices, mapped to the catalogue. Temporary fallback where no shopper price covers a shop | ODbL 1.0, credit Open Food Facts contributors | 17 Oct 2026 (dataset updated 16 Oct 2026) | Cached |
| Open Food Facts product API (`data/off/products.json`) | https://world.openfoodfacts.org/api/v2/product/{barcode} | Name, brand, size, categories, allergens and labels for each barcode in Open Prices | ODbL 1.0 (database), DbCL (contents) | 17 Oct 2026 | Cached |
| Open Food Facts product API, live (`app/scan.py`, cached in the `off_products` table) | https://world.openfoodfacts.org/api/v2/product/{barcode} | Name, brand, size, categories and front photo for each barcode a shopper scans. Falls back to `data/off/products.json` when the API cannot be reached, and says so | ODbL 1.0 (database), DbCL (contents), photos CC BY-SA | Each scan, from 17 Oct 2026 | Live (cached per barcode) |
| Time Series UK Supermarket Data, Kaggle (`data/kaggle/products.csv.gz`) | https://www.kaggle.com/datasets/declanmcalinden/time-series-uk-supermarket-data | Product names per chain (Asda, Aldi, Morrisons, Sainsbury's, Tesco; grocery and household only, 82,414 products) to identify the exact product a shelf label is for. 2024 online prices are the **starting price** of each linked catalogue product at that chain, always shown with their month, until a shopper prices it | Apache 2.0, as stated by the uploader. Attribution and licence copy in `data/kaggle/`. The uploader scraped the supermarkets' websites; the licence covers the uploader's dataset, not any rights the supermarkets hold | 17 Oct 2026 (prices 9 Jan to 13 Apr 2024) | Cached |
| postcodes.io | https://api.postcodes.io | Postcode to lat/lon for the user | Data OGL (ONS Postcode Directory), free API | Per request | Live |
| OpenStreetMap street network, Southampton (`data/streets/`) | https://overpass-api.de/api/interpreter, query in `scripts/fetch_streets.py` | Walk, cycle and road networks (203,081 nodes) for street distances and the route drawn on the map. Routed on our own server (`app/streets.py`), so no location leaves it | ODbL 1.0, credit OpenStreetMap contributors | 17 Oct 2026 (OSM base 20:51 UTC) | Cached |
| OpenFreeMap base map | https://tiles.openfreemap.org/styles/positron (dark: `/styles/dark`) | Map background on the route card, drawn with MapLibre GL | Free, no key, commercial use allowed. OpenMapTiles schema; OpenStreetMap data ODbL 1.0, credited on the map | Per map view | Live |
| Google Maps URLs | https://developers.google.com/maps/documentation/urls | "Directions in Google Maps" link. Only a link: no Google API, nothing sent unless the shopper taps it | Free, no key | Not collected | Link only |

## Synthetic data

How each synthetic set was made, who labelled it, and which part is held out for testing.

| Set | How made | Size | Used for (tuning / test) |
|---|---|---|---|
| Seed prices, `scripts/seed_db.py --synthetic` | Invented base price per product times a per-chain factor, plus noise. Seeded random, rebuilt on each run. Every row has synthetic = 1. Off by default since 17 Oct 2026 | 965 shelf label prices, 34 shops | Demo only. Never used for scoring |
| List item test set, `data/eval/list_items_test.json` | Written by the team with Claude | 45 items | Test only. List prompt has no examples |
| Product class tuning set, `data/eval/class_match_tune.json` | Real Open Food Facts products from `data/off/products.json` (ODbL); answers labelled by Claude Code, to be checked by the team | 12 products | Tuning: examples in the class prompt |
| Product class test set, `data/eval/class_match_test.json` | Same source and labelling, different products from tuning. 15 classes started by one seed product each, plus the 46 catalogue products | 101 products, 43 with a class | Test only |
| Starting price links, `data/kaggle/class_links.json` | `scripts/link_classes.py`: word search shortlist, AI pick per catalogue product and chain, size check. Not yet checked by the team | 158 links, 46 products, 5 chains | Data, not scoring |
| Shelf label test set, `data/eval/label_test.json` and `data/eval/labels/` | `scripts/make_labels.py`: real Kaggle product names picked at random (seeded); prices, member prices, multibuys, was prices and end dates invented; rendered as tilted, blurred photos marked SYNTHETIC TEST LABEL. 6 made-up products not in the list. Answers known by construction | 46 labels, 5 chains | Test only. Label prompts have no examples |

Removed 17 Oct 2026, with receipts: the receipt line tuning and test sets, the exact product test set and the sample receipts. They are in git history.
