# Chain product index

`products.csv.gz` is derived from "Time Series UK Supermarket Data" by Declan McAlinden,
https://www.kaggle.com/datasets/declanmcalinden/time-series-uk-supermarket-data,
licensed Apache 2.0 (copy in `LICENSE-APACHE-2.0.txt`).

Changes made by us: kept grocery and household categories only, one row per chain and product name
with the latest price seen (9 Jan to 13 Apr 2024), dates reformatted. Built by `scripts/fetch_kaggle.py`.

The uploader scraped these prices from the supermarkets' websites. We use the product names to identify
what a receipt line is, and the 2024 prices only as a matching hint. They are never shown as current prices.
