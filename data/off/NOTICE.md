# Open Food Facts data

Both files here are extracts of Open Food Facts databases. They stay under the licences below, separate from our own data.

| File | Source | Licence |
|---|---|---|
| `prices.json` | Open Food Facts Open Prices, https://huggingface.co/datasets/openfoodfacts/open-prices, fetched 17 Oct 2026 by `scripts/fetch_off.py` | Database: ODbL 1.0 |
| `products.json` | Open Food Facts product API, https://world.openfoodfacts.org, fetched 17 Oct 2026 | Database: ODbL 1.0. Individual contents: DbCL 1.0. Product photos (linked, not stored here): CC BY-SA 3.0 |

Attribution: Open Food Facts contributors, https://world.openfoodfacts.org. Licence texts: https://opendatacommons.org/licenses/odbl/1-0/, https://opendatacommons.org/licenses/dbcl/1-0/, https://creativecommons.org/licenses/by-sa/3.0/.

Changes made by us: `prices.json` keeps UK (GBP) prices only and maps some barcodes to our catalogue. `products.json` keeps name, brand, quantity, categories, allergens and labels per barcode.

What share-alike means for us. Anything we build by changing or adding to these files is also ODbL if we share it. This covers the product class eval sets (`data/eval/class_match_*.json`) and the live barcode cache (`off_products` table). It also covers classes and names that come from scanned Open Food Facts products (`products` rows with origin `scan`, `class_members`, and `raw_line` on scan observations). Never mix these into a dataset we sell or license as our own. Shopper prices (store, date, price, our catalogue class) are ours and stay separate. See `docs/data-sources.md`.
