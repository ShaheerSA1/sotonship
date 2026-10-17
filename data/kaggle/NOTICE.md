# Chain product index

`products.csv.gz` is derived from "Time Series UK Supermarket Data" by Declan McAlinden,
https://www.kaggle.com/datasets/declanmcalinden/time-series-uk-supermarket-data,
licensed Apache 2.0 (copy in `LICENSE-APACHE-2.0.txt`).

Changes made by us: kept grocery and household categories only, one row per chain and product name
with the latest price seen (9 Jan to 13 Apr 2024), dates reformatted. Built by `scripts/fetch_kaggle.py`.

How we use it:
- Product names, to match a shelf label to the exact product a chain sells.
- 2024 online prices, as the dated starting price of each linked product (`class_links.json`) until a
  shopper prices it. Always shown with their month and source, never as a current price.

Caution: the uploader scraped these names and prices from the supermarkets' websites. Apache 2.0 covers
the uploader's dataset, not any rights the supermarkets hold in their own product databases. So we do not
redistribute this data as our own and never sell or license it. Before any commercial use, get legal advice
or a licence from the supermarkets, or replace it with shopper prices.

`class_links.json` is ours: which Kaggle product is each catalogue class at each chain, picked by AI and
rules (`scripts/link_classes.py`). It names Kaggle products, so the caution above applies to those names.
