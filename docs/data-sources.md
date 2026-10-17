# Data sources

Every source the product uses. The README must list these with date and licence, so log them here as you add them.

| Source | URL | What we use it for | Licence / terms | Date collected | Live, cached or synthetic |
|---|---|---|---|---|---|
| OpenStreetMap shops, Southampton (`data/stores.json`) | https://overpass-api.de/api/interpreter, query in `scripts/fetch_stores.py` | Shop names, chains, locations, addresses. 62 chain shops kept of 235 | ODbL 1.0, credit OpenStreetMap contributors | 16 Oct 2026 (OSM base 22:56 UTC) | Cached |
| Open Food Facts Open Prices (`data/off/prices.json`) | https://huggingface.co/datasets/openfoodfacts/open-prices (prices.parquet) | UK (GBP) product prices, mapped to the catalogue. Temporary fallback where no community receipt covers a shop | ODbL 1.0, credit Open Food Facts contributors | 17 Oct 2026 (dataset updated 16 Oct 2026) | Cached |
| Open Food Facts product API (`data/off/products.json`) | https://world.openfoodfacts.org/api/v2/product/{barcode} | Name, brand, size, categories, allergens and labels for each barcode in Open Prices | ODbL 1.0 (database), DbCL (contents) | 17 Oct 2026 | Cached |
| postcodes.io | https://api.postcodes.io | Postcode to lat/lon for the user and for receipts | Data OGL (ONS Postcode Directory), free API | Per request | Live |

## Synthetic data

How each synthetic set was made, who labelled it, and which part is held out for testing.

| Set | How made | Size | Used for (tuning / test) |
|---|---|---|---|
| Seed prices, `scripts/seed_db.py` | Invented base price per product times a per-chain factor, plus noise. Seeded random, rebuilt on each run. Every row has synthetic = 1 | 69 receipts, 965 prices, 34 shops | Demo only. Never used for scoring |
| Receipt line tuning set, `data/eval/receipt_lines_tune.json` | Written by the team with Claude, UK receipt style | 10 lines | Tuning: few-shot examples in the receipt prompt |
| Receipt line test set, `data/eval/receipt_lines_test.json` | Written by the team with Claude, different products and abbreviations from tuning | 61 lines, 9 chains | Test only |
| List item test set, `data/eval/list_items_test.json` | Written by the team with Claude | 45 items | Test only. List prompt has no examples |
| Sample receipts, `data/sample_receipts/` | Written by the team with Claude, marked SYNTHETIC in the text. Uploads containing the marker are saved as synthetic | 3 | Demo |
