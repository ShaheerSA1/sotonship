# Nostobon

> Hackathon MVP. Idea and evaluation: [docs/ideas.md](docs/ideas.md).

**Track:** FinTech (proposed)
**Team:** Shaheer Azizi, Nicolas, Kavian, Suhayb

**One sentence:** We help Southampton students cut their weekly grocery bill by pooling the shelf prices shoppers scan and the receipts they upload, and telling them which nearby shops to visit for their list, counting loyalty prices and the time the trip takes.

## The problem

To fill in with evidence gathered at the event: a real student quote, and a published price-gap figure with source and date.

## What it does

Profile is set up once, on first visit, and kept on the device only (browser storage, nothing stored server-side): first name, weekly budget, home location (postcode or device location, geocoded once), travel mode and distance, the 14 UK allergens with an optional strict "may contain" mode, diets (vegetarian, vegan, pescatarian, halal, kosher), loyalty cards (never card numbers), other percentage discounts, shopping priority, most shops per trip and shops to avoid. Everything is editable on the profile page, which also has "download my data" and "delete everything".

1. **Your list.** The home screen is just a greeting and the list. Add items as you would write them, or paste a whole list. The list is remembered.
2. **Plan.** The AI turns the list into products, flags vague items ("crisps: which flavour?") and items we do not track. Rules (not AI) then remove products that clash with the user's allergies and diet. The planner compares every combination of up to three nearby shops and keeps only the routes nobody would rule out (each one quicker than every cheaper one). A slider runs from "Lowest price" to "Least time" and moves between those routes instantly, updating the price, minutes, map, route and basket. It starts where the profile's shopping priority puts it.
3. **Scan prices.** In the shop, scan the pack barcode (camera, or type the digits). Open Food Facts returns the name, brand, size and photo, looked up live. The shopper confirms it is the product in their hand, or says it is wrong and types the name. Then the shelf price, and the member price (Clubcard, Nectar and so on) if the label shows one. Both are kept. Confirmed products are saved on the device, so the next trip is just the price. Checks, all rules: the barcode check digit, codes starting with 2 (printed by the shop for weighed or deli items, so they do not identify the product), own label of a different chain from the shop picked, the same price at the same shop twice in a day, prices far from the usual. The AI then puts the product in a **product class** shared across chains, so Tesco hazelnut spread 400g and Aldi Nutoka 400g are priced as one thing. The 46 catalogue products are the first classes. A product that fits none starts a new class, compared once someone scans the same thing at another chain. The scan screen says which class, who chose it (AI, rules or a shopper) and why, and the shopper can say "Not the same?". Products with no pack size are not compared.
4. **Add a receipt.** Photo, PDF e-receipt or pasted text. The AI reads each line, maps it to a product in our catalogue and picks up loyalty savings (Clubcard Price, Nectar, Lidl Plus). It then works out the **exact product** bought, even when the receipt is vague: Asda prints "CHICKEN 4.30", which could be Shazans thighs, drumsticks or legs. Where one product fits, it says so. Where several fit, the user picks one, or presses Skip and nothing is saved for that line. "Skip all unanswered" clears every question at once. Confirmed picks are remembered for that chain, line and price, so the next shopper gets the answer pre-selected. The user checks and corrects every line before anything is saved. Card numbers, loyalty numbers and the photo are never stored.
5. **Prices.** Every observation, with shop, date and whether it is real or synthetic, plus the Open Food Facts reference prices.

### Where prices come from

For each product at each shop the planner uses the best evidence it has, in this order:

1. A shelf scan or community receipt from that branch. **This is the main source and grows with users.**
2. A shelf scan or community receipt from another branch of the same chain and format.
3. An Open Food Facts Open Prices price for the chain ([Hugging Face dataset](https://huggingface.co/datasets/openfoodfacts/open-prices), ODbL). **Temporary fallback** while receipts are sparse: UK-wide, crowd-sourced, mapped to our catalogue by `scripts/fetch_off.py`.

Every price shown carries its source, date and age, a stale warning after 30 days, and a **synthetic** tag where it is invented test data.

## What the AI does, and why it is needed

Model: `claude-opus-5-5` via the Anthropic Python SDK, structured outputs, server-side refusal fallback. Override with `MODEL` in `.env`.

- **Receipt reading.** Receipts are abbreviated, chain-specific and messy: `WALKERS S/VIN 6X25G`, `Crusti Croc Salt & Vinegar 6x25g` (Lidl own label), `2 @ 0.55`, a Clubcard saving on the line below. The model reads photos and PDFs, which the baseline cannot read at all.
- **List matching.** "dairy milk" is chocolate, "2 milk" is milk, "oat milk" is not tracked, "warburtons" means bread of that brand only.
- **Product class.** Own label has a different barcode at every chain, and the sub-brand often hides the chain (Milbona is Lidl, Cowbelle is Aldi). The model reads the scanned product (name, brand, size, categories) and every class we have, and says same (which class), new, or unsure. It must keep apart variants (whole vs semi-skimmed, mature vs extra mature, organic), sizes more than 10% apart, premium own label (Finest, Deluxe) and brands. Product data goes into the prompt marked as untrusted, and a "same" answer is overruled when the pack sizes we can read differ by more than 10%. Answers are cached per barcode (`app/classes.py`).
- **Exact product.** A word search (no AI, `app/identify.py`) shortlists 25 products the chain sells from the Kaggle product index, ordered by word match and closeness to the price paid. The model then reads the receipt line, the price and the shortlist and says exact, ask (2 to 4 options) or none. Price is used to rule products out, never as the only reason for "exact".

The route planning is plain optimisation (`app/planner.py`), not AI. The barcode lookup (`app/scan.py`) is a lookup plus rules, not AI: own-label detection reads the brand field. Next for the AI: reading shelf labels from a photo (see [docs/ideas.md](docs/ideas.md)).

Remove the AI and photos cannot be read, own-label products are mapped to the wrong brand, and lists are misread. See the numbers below.

## Results vs baseline

Baseline: regex line parser plus fuzzy string matching (`app/baseline.py`), cutoff tuned on the tuning set only.

| Task | Test set | Baseline | AI |
|---|---|---|---|
| Receipt line to product | 61 lines, 9 chains | 80.3% | not run yet (no API key on the dev machine) |
| List item to product group and brand | 45 items | 77.8% | not run yet |
| Exact product among the options offered | 30 lines, 5 chains | 60.0% (18/30), first option right 40.0% | not run yet |
| Scanned product to product class | 101 real products, 43 with a class | 78.2% (79/101), 9 wrong merges, 13 of 43 matches missed | not run yet |

Baseline figures moved on 17 Oct 2026 after a tie-break fix: "milk" scored the same against semi-skimmed milk and Cadbury Dairy Milk, and catalogue order picked the chocolate. Ties now go to own label. Before the fix: 78.7% and 75.6%.

Product class baseline: the catalogue rules in `app/offmap.py`, else a class member with the same Open Food Facts category, size within 10% and the same brand (any own label counts as one). Its misses are Lidl and Aldi sub-brands missing from our brand list (Dairy Manor, Woodcote, Choco Nussa) and odd categories. Its wrong merges are premium and organic packs put with standard own label. A wrong merge is the costly error: two different products priced as one. The test products are real (Open Food Facts, ODbL); the answers were labelled by Claude Code under the rules in the prompt and **still need checking by the team**. The 12 tuning products are the prompt's examples and are not in the test set. Brand names that appear only in the test set are kept out of the prompt.

Exact product also reports confident wrong picks (the model says "exact" and is wrong) and how many questions the user is asked. The baseline never says "exact" and asks on every line.

Run: `.venv/bin/python scripts/eval.py`. Results and every error are written to `data/eval/results.json`.

The receipt and list test sets are **synthetic**, written by the team with AI help in the style of UK receipts and lists. The 10 tuning lines used as prompt examples are in `data/eval/receipt_lines_tune.json` and never appear in the test set. The list and exact product prompts have no examples. Exact product answers are real product names from the Kaggle index; the receipt text and prices paid are ours. Small sets: treat the numbers as indicative.

## Known limits

- **Prices in the demo database are synthetic.** `scripts/seed_db.py` invents them. Real data comes only from uploaded receipts.
- The catalogue has 46 products. Anything else shows as "not tracked".
- Exact product matching covers Asda, Aldi, Morrisons, Sainsbury's and Tesco only (82,414 grocery products). Lidl, Co-op, Iceland and M&S lines show "no product list". The index is not updated after 13 Apr 2024. Its prices are used only inside matching to rule out products that cost far more or less than what was paid, and are not shown to users. Current prices come from receipts. Products launched since April 2024 are missing.
- A branch with no receipt borrows the latest price from another branch of the same chain and format. Flagged in the UI. Express and big stores are kept apart.
- Travel time uses straight-line distance times 1.3 and fixed speeds, not real routes or bus timetables.
- Outlier prices (under 0.4x or over 2.5x the median) are saved but not used until confirmed.
- Shop list is OpenStreetMap as of 16 Oct 2026. Missing or closed shops are not corrected.
- HEIC photos (iPhone default) are rejected. Convert to JPG.
- Barcode lookup needs Open Food Facts to know the product. Unknown barcodes ask the shopper for the name. Its names and sizes are crowd-sourced and sometimes wrong, which is why the shopper confirms each one.
- A scanned product joins a class shared across chains, but only once someone has scanned the other chain's version. New classes start from Open Food Facts data, so their names can be rough, and they have no allergen tags: plans show "no allergen data" for them.
- One shopper pressing "Not the same?" keeps that barcode out of comparison for everyone. There are no accounts, so one person could also flood confirmations or receipt memory. Fine for a demo, needs rate limits and per-user counts before launch.
- Saved products live in the browser's storage on that device only.
- Without an API key the app falls back to the baseline and says so on every screen.
- Open Food Facts has about 2,000 UK prices, mostly from Cardiff and London, and only a fraction map to our 46 products. They are chain-level prices from other towns, used only where no receipt covers a shop, and labelled as such. Promotional prices are ignored, member prices are kept.
- Allergy and diet tags in `data/catalogue.json` are typical for each product type, written by the team, not read from the pack. The UI tells the user to check the label. Halal and kosher rule out all meat because we track no certified meat.

## Business case

To fill in. See the evaluation in [docs/ideas.md](docs/ideas.md#evaluation).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                      # add ANTHROPIC_API_KEY
.venv/bin/python scripts/seed_db.py       # builds data/app.db with SYNTHETIC prices
.venv/bin/python scripts/fetch_off.py     # optional: refresh Open Food Facts prices (data/off/prices.json is committed)
.venv/bin/python scripts/fetch_kaggle.py  # optional: rebuild the chain product index (data/kaggle/ is committed, download ~800 MB)
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000
```

Refresh shop locations: `.venv/bin/python scripts/fetch_stores.py`.

## Android app

`mobile/` is a Capacitor shell. It loads the web app from the server, so there is one codebase: edit `app/static/` and reopen the app (or swipe it away and back) to see the change. No rebuild.

Needs: Node, Android SDK, JDK 21 (in `~/.jdks` or `JAVA_HOME`), phone with USB debugging on.

```bash
cd mobile && npm install
npm run phone      # build APK, install over USB, forward port 8000, open the app
npm run reverse    # after replugging the phone: phone's localhost:8000 -> laptop
```

The server must be running on the laptop (`uvicorn app.main:app --reload`). If it is not reachable the app shows an offline page, not a blank screen.

Rebuild (`npm run phone`) only when something native changes:

- **Server address.** `NOSTOBON_URL=https://... npm run phone` points the app at a hosted server, so it works without the laptop. Default is `http://localhost:8000` over USB.
- **Logo.** Edit `app/static/icons/icon.svg`, then `npm run icons && npm run phone`. Launcher, round, themed (monochrome) icons and splash are all built from that file.
- **Permissions or native plugins.** `mobile/android/app/src/main/AndroidManifest.xml`, `npm install @capacitor/<plugin>`. The camera permission for barcode scanning was added on 17 Oct 2026, so rebuild once with `npm run phone`.

Debug the WebView from the laptop: Chrome, `chrome://inspect`.

## Data sources

| Source | Licence | Date collected | Live / cached / synthetic |
|---|---|---|---|
| OpenStreetMap shop locations, Southampton (`data/stores.json`) | ODbL 1.0 | 16 Oct 2026 | Cached |
| Open Food Facts Open Prices via Hugging Face (`data/off/prices.json`) | ODbL 1.0 | 17 Oct 2026 | Cached |
| Open Food Facts product API, barcode to name and categories (`data/off/products.json`) | ODbL 1.0 | 17 Oct 2026 | Cached |
| Open Food Facts product API, live barcode lookup for scans (cached in `data/app.db`) | ODbL 1.0 | Each scan | Live |
| postcodes.io postcode lookup | Data: OGL (ONS, Royal Mail). Service: free API | Each request | Live |
| Time Series UK Supermarket Data, Kaggle (`data/kaggle/products.csv.gz`): product names and 2024 online prices for 5 chains | Apache 2.0 | Fetched 17 Oct 2026, prices 9 Jan to 13 Apr 2024 | Cached |
| Seed prices (`scripts/seed_db.py`) | Ours | Generated on each seed | Synthetic |
| Eval sets and sample receipts (`data/eval/`, `data/sample_receipts/`) | Ours | 17 Oct 2026 | Synthetic |
| Product class eval (`data/eval/class_match_*.json`): Open Food Facts products, our labels | ODbL 1.0 (products) | 17 Oct 2026 | Real products, labels ours |
| Product catalogue (`data/catalogue.json`) | Ours | 17 Oct 2026 | Written by us |

Full log: [docs/data-sources.md](docs/data-sources.md).

## AI disclosure

- Repository structure, docs and parts of the code were generated with Claude (Anthropic) via Claude Code.
- Generated with Claude Code on 17 Oct 2026: the rename to Nostobon, the one-time profile setup and profile page, the list-first home screen, the price and time slider over the route frontier with map, allergy and diet filtering (`app/diet.py` and catalogue tags), the Open Food Facts import (`scripts/fetch_off.py`) and fallback pricing in `app/planner.py`.
- Generated with Claude Code on 17 Oct 2026: the whole MVP in `app/` (backend and frontend), `scripts/`, `data/catalogue.json`, the synthetic eval sets in `data/eval/`, the synthetic sample receipts, and this README.
- Generated with Claude Code on 17 Oct 2026: the Android app in `mobile/` (Capacitor config, offline page, icon and splash generator, build scripts). `mobile/android/` is the Capacitor template.
- Generated with Claude Code on 17 Oct 2026: exact product matching (`app/identify.py`, `scripts/fetch_kaggle.py`, the pick prompt in `app/ai.py`, the "which one did you buy?" step in the receipt screen), the exact product test set and eval task, the baseline tie-break fix.
- Generated with Claude Code on 17 Oct 2026: product classes across chains (`app/classes.py`, the class prompt in `app/ai.py`, the class tables in `app/db.py`, the class note on the Scan screen), the product class test set and its labels, and eval task 4.
- Generated with Claude Code on 17 Oct 2026: barcode scanning (`app/scan.py`, `app/offmap.py` moved out of `scripts/fetch_off.py`, the scan endpoints in `app/main.py`, the Scan screen and saved products in `app/static/`, the Android camera permission).
- Pre-existing work: none. Repo created after hacking opened on Fri 16 Oct 2026 20:00.
- Outside help: none yet.

## Team docs

Briefs, judging rules and planning live in [`docs/`](docs/). Start with [docs/event.md](docs/event.md).
