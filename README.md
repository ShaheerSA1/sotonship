# Nostobon

> Hackathon MVP. Idea and evaluation: [docs/ideas.md](docs/ideas.md).

**Track:** Southampton City
**Team:** Shaheer Azizi, Nicolas, Kavian, Suhayb

**One sentence:** We help Southampton students cut their weekly grocery bill by pooling the shelf prices shoppers scan in local shops, and telling them which nearby shops to visit for their list, counting loyalty prices and the time the trip takes.

## The problem

To fill in with local evidence gathered at the event: a real Southampton student quote, and a published price-gap or cost-of-living figure for Southampton with source and date (for example from the Southampton Data Observatory).

## What it does

Profile is set up once, on first visit, and kept on the device only (browser storage, nothing stored server-side): first name, weekly budget, home location (postcode or device location, geocoded once), travel mode and distance, the 14 UK allergens with an optional strict "may contain" mode, diets (vegetarian, vegan, pescatarian, halal, kosher), loyalty cards (never card numbers), other percentage discounts, shopping priority, most shops per trip and shops to avoid. Everything is editable on the profile page, which also has "download my data" and "delete everything".

1. **Your list.** The home screen is just a greeting and the list. Add items as you would write them, or paste a whole list. The list is remembered.
2. **Plan.** The AI turns the list into products, flags vague items ("crisps: which flavour?") and items we do not track. Rules (not AI) then remove products that clash with the user's allergies and diet. The planner compares every combination of up to three nearby shops and keeps only the routes nobody would rule out (each one quicker than every cheaper one). A slider runs from "Lowest price" to "Least time" and moves between those routes instantly, updating the price, minutes, map, route and basket. It starts where the profile's shopping priority puts it.
3. **Shelf label photo.** In the shop, take a photo of the shelf label. The AI reads the description, size, shelf price, member price and scheme (Clubcard, Nectar, Lidl Plus, More Card), multibuy ("Any 3 for £5", members only or not), "was" price and the offer end date. A word search shortlists products that chain sells (Kaggle product list) and the AI picks the one the label is for, or asks, or says none. Every field is editable before saving. Rules then check the read: member price lower than shelf price, offer not already ended, label style matches the shop, other labels in the photo, fields the AI could not read. The product is saved on the device under "Your products", so next time the card opens with the last prices filled in and the shopper only changes what is different. An offer past its end date is cleared. No photo or no AI: type what the label says and rules read it instead.
4. **Scan a barcode.** In the shop, scan the pack barcode (camera, or type the digits). Open Food Facts returns the name, brand, size and photo, looked up live. The shopper confirms it is the product in their hand, or says it is wrong and types the name. Then the shelf price, and the member price (Clubcard, Nectar and so on) if the label shows one. Both are kept. Confirmed products are saved on the device, so the next trip is just the price. Checks, all rules: the barcode check digit, codes starting with 2 (printed by the shop for weighed or deli items, so they do not identify the product), own label of a different chain from the shop picked, the same price at the same shop twice in a day, prices far from the usual. The AI then puts the product in a **product class** shared across chains, so Tesco hazelnut spread 400g and Aldi Nutoka 400g are priced as one thing. The 46 catalogue products are the first classes. A product that fits none starts a new class, compared once someone scans the same thing at another chain. The scan screen says which class, who chose it (AI, rules or a shopper) and why, and the shopper can say "Not the same?". Products with no pack size are not compared.

The Prices screen (every price for one product) is hidden for now. Its code is kept in `app/static/app.js`, and `/api/prices/{product_id}` still works.

### Where prices come from

For each product at each shop the planner uses the best evidence it has, in this order:

1. A shelf label or barcode scan from that branch. **This is the main source and grows with users.**
2. The same from another branch of the same chain and format.
3. An Open Food Facts Open Prices price for the chain ([Hugging Face dataset](https://huggingface.co/datasets/openfoodfacts/open-prices), ODbL): UK-wide, crowd-sourced, mapped to our catalogue by `scripts/fetch_off.py`.
4. **Starting price:** the chain's online price from the [Kaggle supermarket set](https://www.kaggle.com/datasets/declanmcalinden/time-series-uk-supermarket-data) (Apache 2.0, 9 Jan to 13 Apr 2024). `scripts/link_classes.py` links each catalogue product to the product each chain sells (`data/kaggle/class_links.json`), so every product has a price at Asda, Aldi, Morrisons, Sainsbury's and Tesco before any shopper has priced it. A shelf label for a linked product replaces it.

Offers count only while they last: a member price or multibuy past the end date on its label is dropped, and a shelf price that was itself the offer goes back to the "was" price. A multibuy counts when the list asks for enough of that product, and a members-only multibuy only with the card.

Every price shown carries its source, date and age, a stale warning after 30 days (starting prices are tagged "online price" with their month instead), and a **synthetic** tag where it is invented test data.

## What the AI does, and why it is needed

Model: `claude-haiku-5-5` (Claude Haiku 5.5) via the Anthropic Python SDK, structured outputs. Override with `MODEL` in `.env`. Haiku has no server-side refusal fallback, so a refusal is shown to the user as an error. Other models (for example `claude-opus-5-5`) also get the server-side fallback.

- **List matching.** "dairy milk" is chocolate, "2 milk" is milk, "oat milk" is not tracked, "warburtons" means bread of that brand only.
- **Product class.** Own label has a different barcode at every chain, and the sub-brand often hides the chain (Milbona is Lidl, Cowbelle is Aldi). The model reads the scanned product (name, brand, size, categories) and every class we have, and says same (which class), new, or unsure. It must keep apart variants (whole vs semi-skimmed, mature vs extra mature, organic), sizes more than 10% apart, premium own label (Finest, Deluxe) and brands. Product data goes into the prompt marked as untrusted, and a "same" answer is overruled when the pack sizes we can read differ by more than 10%. Answers are cached per barcode (`app/classes.py`).
- **Shelf label reading** (`app/labels.py`). Labels differ by chain, offers are printed in bands and small print ("Clubcard Price", "Regular price", "Any 2 for £3.50", "Ends 21/10"), and photos are tilted and blurred. The model reads the photo into structured fields. A word search (no AI, `app/identify.py`) then shortlists 25 products the chain sells from the Kaggle product index, ordered by word match and closeness to the label price, and the model picks the one the label is for, asks (2 to 4 options) or says none. Price is used to rule products out, never as the only reason for "exact". A pick whose readable size differs by more than 10% from the label becomes a question. Dates with no year go to the nearest year, so a label that ended last week reads as ended.
- **Starting price links** (`scripts/link_classes.py`, run once, output committed). For each catalogue product and chain the model picks the product that is the same variant, tier and size within 10%, or none. Picks with a readable size more than 10% off are dropped. Without a key, rules pick instead and each link says which.

The route planning is plain optimisation (`app/planner.py`), not AI. The barcode lookup (`app/scan.py`) is a lookup plus rules, not AI: own-label detection reads the brand field.

Remove the AI and shelf label photos cannot be read, own-label products are mapped to the wrong brand, and lists are misread. See the numbers below.

## Results vs baseline

Baseline: fuzzy string matching for lists, and regexes plus word search for shelf labels (`app/baseline.py`). The fuzzy cutoff was tuned on a tuning set (the old receipt tuning lines, now in git history only), never on a test set.

| Task | Test set | Baseline | Claude Haiku 5.5 (our model) | Claude Opus 5.5, for comparison |
|---|---|---|---|---|
| List item to product group and brand | 45 items | 77.8% (35/45) | **91.1% (41/45)** | 97.8% (44/45) |
| Scanned product to product class | 101 real products, 43 with a class | 78.2% (79/101), 9 wrong merges, 13 of 43 matches missed | **86.1% (87/101)**, 12 wrong merges, 2 of 43 missed | 98.0% (99/101), 1 wrong merge |
| Shelf label to product and prices | 46 synthetic label photos, 5 chains, 6 products not in the list | 87.0% (40/46) product offered, asks on all 46, every price right 46/46, **given the label text typed perfectly** | **100% (46/46)** product offered, first option right 100%, asks on 2, 0 confident wrong, every price right 46/46, from the photo | not run |

Runs, all 17 Oct 2026 (`data/eval/results.json`, models as recorded in the file): Haiku 5.5 at 16:22 BST, Opus 5.5 at 14:41 BST. The prompts did not change between the two runs, so the gap is the model. Haiku costs about a fortieth of Opus per token ($0.10 / $0.50 per million input / output tokens, against $4 / $20). The cost of Haiku shows most in product class: 12 wrong merges against Opus's 1. One run each, so treat the numbers as indicative.

The baseline was rerun on 17 Oct 2026 after receipts were removed. Its numbers did not change. The last AI results are kept in `results.json` under `ai_previous` until someone reruns the eval with a key.

- Product class: Haiku makes more wrong merges than the baseline (12 vs 9). Several are disputed labels rather than clear errors (Yorkshire Tea 80 bags put in the Yorkshire Tea 80 class, labelled "no class"), which is one more reason the team must check the labels.
- Shelf label: the photos are rendered by `scripts/make_labels.py`, clean and evenly lit. Real shelf photos (glare, angle, worn labels, several labels in frame) will score lower. Treat 100% as an upper bound until real photos are tested. The answers are known by construction, nobody labelled them. The baseline's 6 misses are the 6 made-up products: word search always offers something.

Baseline figures moved on 17 Oct 2026 after a tie-break fix: "milk" scored the same against semi-skimmed milk and Cadbury Dairy Milk, and catalogue order picked the chocolate. Ties now go to own label. List matching before the fix: 75.6%.

Product class baseline: the catalogue rules in `app/offmap.py`, else a class member with the same Open Food Facts category, size within 10% and the same brand (any own label counts as one). Its misses are Lidl and Aldi sub-brands missing from our brand list (Dairy Manor, Woodcote, Choco Nussa) and odd categories. Its wrong merges are premium and organic packs put with standard own label. A wrong merge is the costly error: two different products priced as one. The test products are real (Open Food Facts, ODbL); the answers were labelled by Claude Code under the rules in the prompt and **still need checking by the team**. The labeller and the model under test are both Claude, so until the team checks the labels the product class figures can be off either way. The 12 tuning products are the prompt's examples and are not in the test set. Brand names that appear only in the test set are kept out of the prompt.

The shelf label task measures the read (shelf, member, was price, multibuy, end date) and the product pick together, and also counts confident wrong picks (the model says "exact" and is wrong) and how many questions the shopper is asked. The label prompts have no examples, so there is no tuning split.

Run: `.venv/bin/python scripts/eval.py`. Results and every error are written to `data/eval/results.json`. A failed AI call is never replaced by the baseline: the task is reported as failed, or for product class the item counts as wrong and the failure count is printed.

The list test set is **synthetic**, written by the team with AI help in the style of UK shopping lists. The list prompt has no examples. Small sets: treat the numbers as indicative.

## Known limits

- **Starting prices are 2024 online prices.** Prices have risen since, and shops, Express stores especially, can charge more than the website. They are tagged with their month everywhere they appear. They have no member prices or offers: those come only from shelf labels.
- **Starting price links were made by the AI and are not yet checked by the team** (`data/kaggle/class_links.json`, `by: ai`). 158 of 230 class and chain pairs are linked: Sainsbury's 42, Morrisons 40, Tesco 38, Aldi 22, Asda 16. Asda names often have no pack size, so most were left unlinked rather than guessed. One suspect link: Tesco "Golden Granulated Sugar 1kg" for plain granulated sugar. Set `by` to `team` on links you check.
- A shelf label is compared across shops only when its product is one of the linked catalogue products. Other labels are saved and shown in "Your products" but not used in plans yet.
- Lidl, Co-op, Iceland and M&S have no product list, so their labels are saved under the name on the label and not compared.
- Multibuys count only for one product ("3 for £5" on the same item), not mixed "any 3" deals across products.
- `scripts/seed_db.py` now builds an empty database by default. `--synthetic` adds invented shelf label prices, which outrank starting prices at the shops they cover.
- The catalogue has 46 products. Anything else shows as "not tracked".
- Matching a shelf label to an exact product covers Asda, Aldi, Morrisons, Sainsbury's and Tesco only (82,414 grocery products). The index is not updated after 13 Apr 2024, so products launched since then are missing. Its prices are shown only as dated starting prices. Current prices come from shelf labels and scans.
- A branch with no shopper price borrows the latest price from another branch of the same chain and format. Flagged in the UI. Express and big stores are kept apart.
- Travel time uses straight-line distance times 1.3 and fixed speeds, not real routes or bus timetables.
- Outlier prices (under 0.4x or over 2.5x the median) are saved but not used until confirmed.
- Shop list is OpenStreetMap as of 16 Oct 2026. Missing or closed shops are not corrected.
- Shelf label photos are converted to JPEG in the browser when the browser can open them (Safari can), else rejected with a message.
- Barcode lookup needs Open Food Facts to know the product. Unknown barcodes ask the shopper for the name. Its names and sizes are crowd-sourced and sometimes wrong, which is why the shopper confirms each one.
- A scanned product joins a class shared across chains, but only once someone has scanned the other chain's version. New classes start from Open Food Facts data, so their names can be rough, and they have no allergen tags: plans show "no allergen data" for them.
- One shopper pressing "Not the same?" keeps that barcode out of comparison for everyone. There are no accounts, so one person could also flood confirmations or prices. Fine for a demo, needs rate limits and per-user counts before launch.
- Saved products live in the browser's storage on that device only.
- Without an API key the app falls back to the baseline and says so on every screen.
- Open Food Facts has about 2,000 UK prices, mostly from Cardiff and London, and only a fraction map to our 46 products. They are chain-level prices from other towns, used only where no shopper price covers a shop, and labelled as such. Promotional prices are ignored, member prices are kept.
- Allergy and diet tags in `data/catalogue.json` are typical for each product type, written by the team, not read from the pack. The UI tells the user to check the label. Halal and kosher rule out all meat because we track no certified meat.

## Business case

To fill in. See the evaluation in [docs/ideas.md](docs/ideas.md#evaluation).

The Southampton City pitch must answer three questions (see [the brief](docs/briefs/southampton-city.md)):

1. What local evidence shows the problem is real in Southampton?
2. Who would own and pay for the product?
3. What would it take to run it in a second city?

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                      # add ANTHROPIC_API_KEY
.venv/bin/python scripts/seed_db.py       # builds an empty data/app.db; add --synthetic for invented demo prices
.venv/bin/python scripts/fetch_off.py     # optional: refresh Open Food Facts prices (data/off/prices.json is committed)
.venv/bin/python scripts/fetch_kaggle.py  # optional: rebuild the chain product index (data/kaggle/ is committed, download ~800 MB)
.venv/bin/python scripts/link_classes.py  # optional: relink catalogue products to each chain's product (AI, output committed)
.venv/bin/python scripts/make_labels.py   # optional: rebuild the synthetic label test set (needs pip install pillow)
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
| Time Series UK Supermarket Data, Kaggle (`data/kaggle/products.csv.gz`): product names and 2024 online prices for 5 chains, the starting price for each linked product | Apache 2.0 | Fetched 17 Oct 2026, prices 9 Jan to 13 Apr 2024 | Cached |
| Starting price links (`data/kaggle/class_links.json`): catalogue product to Kaggle product per chain, picked by AI | Ours | 17 Oct 2026 | Derived, not yet checked by the team |
| Shelf label test set (`data/eval/label_test.json`, `data/eval/labels/`): real Kaggle product names, invented prices and offers, rendered images | Ours (names from Kaggle, Apache 2.0) | 17 Oct 2026 | Synthetic |
| Seed prices (`scripts/seed_db.py`) | Ours | Generated on each seed | Synthetic |
| List eval set (`data/eval/list_items_test.json`) | Ours | 17 Oct 2026 | Synthetic |
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
- Generated with Claude Code on 17 Oct 2026: eval hardening (AI failures no longer fall back to the baseline inside the AI score, one failed task no longer drops the others) and the AI results above.
- Generated with Claude Code on 17 Oct 2026: barcode scanning (`app/scan.py`, `app/offmap.py` moved out of `scripts/fetch_off.py`, the scan endpoints in `app/main.py`, the Scan screen and saved products in `app/static/`, the Android camera permission).
- Generated with Claude Code on 17 Oct 2026: Kaggle prices as the starting price (`scripts/link_classes.py`, `data/kaggle/class_links.json`, `class_links` table, the fourth price source in `app/planner.py`), shelf label photos (`app/labels.py`, the label prompts in `app/ai.py`, the label reader in `app/baseline.py`, the label endpoints in `app/main.py`, the label card and saved-product repricing on the Scan screen), offer end dates, "was" prices and multibuys in the database and planner, the synthetic label test set (`scripts/make_labels.py`) and eval task 5, and the results above.
- Generated with Claude Code on 17 Oct 2026: receipts removed from the app, eval and data (the project is shelf labels and barcode scans only now), the Prices screen hidden, Claude Haiku 5.5 made the default model, the track changed to Southampton City, and the results above corrected to name the model of each run.
- Pre-existing work: none. Repo created after hacking opened on Fri 16 Oct 2026 20:00.
- Outside help: none yet.

## Team docs

Briefs, judging rules and planning live in [`docs/`](docs/). Start with [docs/event.md](docs/event.md).
