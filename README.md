# Nostobon

> Hackathon MVP. Idea and evaluation: [docs/ideas.md](docs/ideas.md).

**Track:** FinTech (proposed)
**Team:** Shaheer Azizi, Nicolas, Kavian, Suhayb

**One sentence:** We help Southampton students cut their weekly grocery bill by reading the receipts the community uploads and telling them which nearby shops to visit for their list, counting loyalty prices and the time the trip takes.

## The problem

To fill in with evidence gathered at the event: a real student quote, and a published price-gap figure with source and date.

## What it does

Profile is set up once, on first visit, and kept on the device only (browser storage, nothing stored server-side): first name, weekly budget, home location (postcode or device location, geocoded once), travel mode and distance, the 14 UK allergens with an optional strict "may contain" mode, diets (vegetarian, vegan, pescatarian, halal, kosher), loyalty cards (never card numbers), other percentage discounts, shopping priority, most shops per trip and shops to avoid. Everything is editable on the profile page, which also has "download my data" and "delete everything".

1. **Your list.** The home screen is just a greeting and the list. Add items as you would write them, or paste a whole list. The list is remembered.
2. **Plan.** The AI turns the list into products, flags vague items ("crisps: which flavour?") and items we do not track. Rules (not AI) then remove products that clash with the user's allergies and diet. The planner compares every combination of up to three nearby shops and keeps only the routes nobody would rule out (each one quicker than every cheaper one). A slider runs from "Lowest price" to "Least time" and moves between those routes instantly, updating the price, minutes, map, route and basket. It starts where the profile's shopping priority puts it.
3. **Add a receipt.** Photo, PDF e-receipt or pasted text. The AI reads each line, maps it to a product in our catalogue and picks up loyalty savings (Clubcard Price, Nectar, Lidl Plus). The user checks and corrects every line before anything is saved. Card numbers, loyalty numbers and the photo are never stored.
4. **Prices.** Every observation, with shop, date and whether it is real or synthetic, plus the Open Food Facts reference prices.

### Where prices come from

For each product at each shop the planner uses the best evidence it has, in this order:

1. A community receipt from that branch. **This is the main source and grows with users.**
2. A community receipt from another branch of the same chain and format.
3. An Open Food Facts Open Prices price for the chain ([Hugging Face dataset](https://huggingface.co/datasets/openfoodfacts/open-prices), ODbL). **Temporary fallback** while receipts are sparse: UK-wide, crowd-sourced, mapped to our catalogue by `scripts/fetch_off.py`.

Every price shown carries its source, date and age, a stale warning after 30 days, and a **synthetic** tag where it is invented test data.

## What the AI does, and why it is needed

Model: `claude-opus-5-5` via the Anthropic Python SDK, structured outputs, server-side refusal fallback. Override with `MODEL` in `.env`.

- **Receipt reading.** Receipts are abbreviated, chain-specific and messy: `WALKERS S/VIN 6X25G`, `Crusti Croc Salt & Vinegar 6x25g` (Lidl own label), `2 @ 0.55`, a Clubcard saving on the line below. The model reads photos and PDFs, which the baseline cannot read at all.
- **List matching.** "dairy milk" is chocolate, "2 milk" is milk, "oat milk" is not tracked, "warburtons" means bread of that brand only.

The route planning is plain optimisation (`app/planner.py`), not AI.

Remove the AI and photos cannot be read, own-label products are mapped to the wrong brand, and lists are misread. See the numbers below.

## Results vs baseline

Baseline: regex line parser plus fuzzy string matching (`app/baseline.py`), cutoff tuned on the tuning set only.

| Task | Test set | Baseline | AI |
|---|---|---|---|
| Receipt line to product | 61 lines, 9 chains | 78.7% | not run yet (no API key on the dev machine) |
| List item to product group and brand | 45 items | 75.6% | not run yet |

Run: `.venv/bin/python scripts/eval.py`. Results and every error are written to `data/eval/results.json`.

Both test sets are **synthetic**, written by the team with AI help in the style of UK receipts and lists. The 10 tuning lines used as prompt examples are in `data/eval/receipt_lines_tune.json` and never appear in the test set. The list prompt has no examples. Small sets: treat the numbers as indicative.

## Known limits

- **Prices in the demo database are synthetic.** `scripts/seed_db.py` invents them. Real data comes only from uploaded receipts.
- The catalogue has 46 products. Anything else shows as "not tracked".
- A branch with no receipt borrows the latest price from another branch of the same chain and format. Flagged in the UI. Express and big stores are kept apart.
- Travel time uses straight-line distance times 1.3 and fixed speeds, not real routes or bus timetables.
- Outlier prices (under 0.4x or over 2.5x the median) are saved but not used until confirmed.
- Shop list is OpenStreetMap as of 16 Oct 2026. Missing or closed shops are not corrected.
- HEIC photos (iPhone default) are rejected. Convert to JPG.
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
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000
```

Refresh shop locations: `.venv/bin/python scripts/fetch_stores.py`.

## Data sources

| Source | Licence | Date collected | Live / cached / synthetic |
|---|---|---|---|
| OpenStreetMap shop locations, Southampton (`data/stores.json`) | ODbL 1.0 | 16 Oct 2026 | Cached |
| Open Food Facts Open Prices via Hugging Face (`data/off/prices.json`) | ODbL 1.0 | 17 Oct 2026 | Cached |
| Open Food Facts product API, barcode to name and categories (`data/off/products.json`) | ODbL 1.0 | 17 Oct 2026 | Cached |
| postcodes.io postcode lookup | Data: OGL (ONS, Royal Mail). Service: free API | Each request | Live |
| Seed prices (`scripts/seed_db.py`) | Ours | Generated on each seed | Synthetic |
| Eval sets and sample receipts (`data/eval/`, `data/sample_receipts/`) | Ours | 17 Oct 2026 | Synthetic |
| Product catalogue (`data/catalogue.json`) | Ours | 17 Oct 2026 | Written by us |

Full log: [docs/data-sources.md](docs/data-sources.md).

## AI disclosure

- Repository structure, docs and parts of the code were generated with Claude (Anthropic) via Claude Code.
- Generated with Claude Code on 17 Oct 2026: the rename to Nostobon, the one-time profile setup and profile page, the list-first home screen, the price and time slider over the route frontier with map, allergy and diet filtering (`app/diet.py` and catalogue tags), the Open Food Facts import (`scripts/fetch_off.py`) and fallback pricing in `app/planner.py`.
- Generated with Claude Code on 17 Oct 2026: the whole MVP in `app/` (backend and frontend), `scripts/`, `data/catalogue.json`, the synthetic eval sets in `data/eval/`, the synthetic sample receipts, and this README.
- Pre-existing work: none. Repo created after hacking opened on Fri 16 Oct 2026 20:00.
- Outside help: none yet.

## Team docs

Briefs, judging rules and planning live in [`docs/`](docs/). Start with [docs/event.md](docs/event.md).
