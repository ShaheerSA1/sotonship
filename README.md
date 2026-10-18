# Nostobon

> Hackathon MVP. Idea and evaluation: [docs/ideas.md](docs/ideas.md).

**Track:** Southampton City
**Team:** Shaheer Azizi, Nicolas, Kavian, Suhayb

**One sentence:** We help Southampton students cut their weekly grocery bill by pooling the shelf prices shoppers scan in local shops, and telling them which nearby shops to visit for their list, counting loyalty prices and the time the trip takes.

## The problem

To fill in with local evidence gathered at the event: a real Southampton student quote, and a published price-gap or cost-of-living figure for Southampton with source and date (for example from the Southampton Data Observatory).

## What it does

Profile is set up once, on first visit, and kept on the device only (browser storage, nothing stored server-side): first name, weekly budget, home location (postcode or device location, geocoded once), travel mode and distance, the 14 UK allergens with an optional strict "may contain" mode, diets (vegetarian, vegan, pescatarian, halal, kosher), loyalty cards (never card numbers), other percentage discounts, shopping priority, most shops per trip and shops to avoid. Everything is editable on the profile page, which also has "download my data" and "delete everything". The weekly budget counts only shops the user confirmed, Monday to Sunday, also kept on the device.

1. **Your list.** The home screen is just a greeting and the list. Add items as you would write them, or paste a whole list. The list is remembered. Under the box, "Buy again" shows what you bought before as one-tap chips, ranked by how many trips each item was on, with newer trips counting more. Items on at least half your last 10 trips (and at least 3) are "usuals", shaded green, and "Add usuals" adds them all at once. A tapped chip stays in place with a tick, so tapping lots in a row never hits a chip that moved; tap it again to undo, and the box tidies up 1.5 seconds after the last tap. Typing filters the chips. "Show all" opens the full set, and "Edit" there stops suggesting an item. A trip is a day you confirmed a shop (only the items ticked as got count) or a day a household item got ticked off. Planning a list or scanning a product never adds to it. The history stays on the device (browser storage). Rules only, no AI.
2. **Plan.** The AI turns the list into products, flags vague items ("crisps: which flavour?") and items we do not track. An item with no variant ("pasta sauce") takes the cheapest product of that type. An item with a variant ("veg pasta sauce") also allows close swaps that do the same job (another tomato pasta sauce, never carbonara), and the plan marks any swap it picks. A named brand ("mutti pasta sauce") means that brand only. An amount ("1kg penne", "12 eggs") is turned into packs by rules: 2 x 500g, 2 x 6. Pack sizes that no number of packs fits within 90% to 150% are left out, and if nothing is that small the smallest bigger pack is used and the plan says so. Rules (not AI) then remove products that clash with the user's allergies and diet. Above "Find my shops" the shopper picks where the trip starts: "From home" (the profile location, there and back) or "From where I am now" (a fresh phone location, kept in memory for this visit only and taken again after 5 minutes), then finishes at home or back where they are. The plan names both ends with the postcode and the time the location was taken, and the map, route and Google Maps link run start to finish. A shop counts as in range when it is within the distance of either end. The planner compares every combination of up to three nearby shops and keeps only the routes nobody would rule out (each one quicker than every cheaper one). A slider runs from "Lowest price" to "Least time" and moves between those routes instantly, updating the price, minutes, map, route and basket. It starts where the profile's shopping priority puts it. With one route only, the plan says why: a quicker route that cannot get everything is named, with what it is missing.
3. **Shelf label photo.** In the shop, take a photo of the shelf label. The AI reads the description, size, shelf price, member price and scheme (Clubcard, Nectar, Lidl Plus, More Card), multibuy ("Any 3 for £5", members only or not), "was" price and the offer end date. A word search shortlists products that chain sells (Kaggle product list) and the AI picks the one the label is for, or asks, or says none. Every field is editable before saving. Rules then check the read: member price lower than shelf price, offer not already ended, label style matches the shop, other labels in the photo, fields the AI could not read. The product is saved on the device under "Your products", so next time the card opens with the last prices filled in and the shopper only changes what is different. An offer past its end date is cleared. No photo or no AI: type what the label says and rules read it instead.
4. **Scan a barcode.** In the shop, scan the pack barcode (camera, or type the digits). Open Food Facts returns the name, brand, size and photo, looked up live. The shopper confirms it is the product in their hand, or says it is wrong and types the name. Then the shelf price, and the member price (Clubcard, Nectar and so on) if the label shows one. Both are kept. Confirmed products are saved on the device, so the next trip is just the price. Checks, all rules: the barcode check digit, codes starting with 2 (printed by the shop for weighed or deli items, so they do not identify the product), own label of a different chain from the shop picked, the same price at the same shop twice in a day, prices far from the usual. The AI then puts the product in a **product class** shared across chains, so Tesco hazelnut spread 400g and Aldi Nutoka 400g are priced as one thing. The 76 catalogue products are the first classes. A product that fits none starts a new class, and the AI then links it to the same product at every other chain in the background, so a plan can compare shops for it straight away. The scan screen says which class, who chose it (AI, rules or a shopper) and why, and the shopper can say "Not the same?". Products with no pack size are not compared.
5. **Household.** One shopping list shared by everyone at home, run like a WhatsApp group. Whoever starts it is the owner and gets a 6-character join code. Everyone who joins is a member. Members add to the list and remove what they added. The owner and admins remove any item, clear bought items, make or dismiss admins and remove people. Nobody can remove the owner or change their role. If the owner leaves, the longest-serving admin (else member) takes over. Removing anything takes two taps: × first, then a red confirm button. Anyone can tick an item off. It stays struck through for 4 seconds with Undo, then moves to Bought, and the list shows who bought it. "Choose what to put on my list" lets a member tick just the items they will buy (or "Select all") and adds those to their own list, tagged "household", so the planner prices them. Items already on their list show "on your list". Adding them also claims them, so everyone else sees "Shaheer is getting this" and cannot pick them too. If someone claimed an item first, it is left off with a message saying who. A claim ends when the item is bought, when the claimer takes it off their list or leaves, when an admin frees it, or after 24 hours. "Invite" shares the join code (or copies it). The same "Buy again" chips sit under the add box. Adds show on the list at once and go to the server one at a time. Rules only, no AI. Every rule is checked on the server (`app/household.py`). The screen refreshes every 4 seconds while open and as soon as the app comes back to the front, so phones on the same server see each other's changes within seconds.
6. **Confirm the shop.** The plan page ends with "Done the shop?". "I've done this shop" opens a check screen with two parts. First, what you got: every item on the list, ticked by default, so the shopper unticks what they did not get. Second, the shelf price of each product in the chosen route, filled in from the plan, so the shopper can correct any that were wrong. "Confirm shop" then saves only the prices that were changed, as shopper prices (`/api/trips`, method `trip`, same outlier check as labels). It ticks off, for everyone, the household items that were picked and bought, and removes what was bought from the list and adds it to "Buy again". Unticked items stay on the list for next time. If saving the prices fails, nothing else changes. A summary says what was cleared, ticked off and updated, and the route stays one tap away.

The Prices screen (every price for one product) is hidden for now. Its code is kept in `app/static/app.js`, and `/api/prices/{product_id}` still works.

### Where prices come from

For each product at each shop the planner uses the best evidence it has, in this order:

1. A shelf label, barcode scan or price corrected after a shop, from that branch. **This is the main source and grows with users.**
2. The same from another branch of the same chain and format.
3. An Open Food Facts Open Prices price for the chain ([Hugging Face dataset](https://huggingface.co/datasets/openfoodfacts/open-prices), ODbL): UK-wide, crowd-sourced, mapped to our catalogue by `scripts/fetch_off.py`.
4. **Starting price:** the chain's online price from the [Kaggle supermarket set](https://www.kaggle.com/datasets/declanmcalinden/time-series-uk-supermarket-data) (Apache 2.0, 9 Jan to 13 Apr 2024). `scripts/link_classes.py` links each catalogue product to the product each chain sells (`data/kaggle/class_links.json`), so every product has a price at Asda, Aldi, Morrisons, Sainsbury's and Tesco before any shopper has priced it. A shelf label for a linked product replaces it.

Offers count only while they last: a member price or multibuy past the end date on its label is dropped, and a shelf price that was itself the offer goes back to the "was" price. A multibuy counts when the list asks for enough of that product, and a members-only multibuy only with the card.

Every price shown carries its source, date and age, a stale warning after 30 days (starting prices are tagged "online price" with their month instead), and a **synthetic** tag where it is invented test data.

## What the AI does, and why it is needed

Model: `claude-haiku-5-5` (Claude Haiku 5.5) via the Anthropic Python SDK, structured outputs. Override with `MODEL` in `.env`. Haiku has no server-side refusal fallback, so a refusal is shown to the user as an error. Other models (for example `claude-opus-5-5`) also get the server-side fallback.

- **List matching.** "dairy milk" is chocolate, "2 milk" is milk, "oat milk" is not tracked, "warburtons" means bread of that brand only. It also reads the amount asked for ("1kg pasta" is a size, "2 pasta" is a count) and the close swaps for an item with a variant. The pack arithmetic is rules (`fit_sizes` in `app/planner.py`).
- **Product class.** Own label has a different barcode at every chain, and the sub-brand often hides the chain (Milbona is Lidl, Cowbelle is Aldi). The model reads the scanned product (name, brand, size, categories) and every class we have, and says same (which class), new, or unsure. It must keep apart variants (whole vs semi-skimmed, mature vs extra mature, organic, flavour), sizes more than 10% apart, brands, and three own label tiers: value (Stamford Street, Hubbard's, Just Essentials, Stockwell, Savers), standard, and premium (Finest, Taste the Difference). So Hubbard's, Sainsbury's own, Taste the Difference, Dolmio and Mutti pasta sauce are five different products. When unsure between same and new it says new: a wrong merge prices two products as one. Product data goes into the prompt marked as untrusted, and a "same" answer is overruled when the pack sizes we can read differ by more than 10%. Answers are cached per barcode (`app/classes.py`).
- **Shelf label reading** (`app/labels.py`). Labels differ by chain, offers are printed in bands and small print ("Clubcard Price", "Regular price", "Any 2 for £3.50", "Ends 21/10"), and photos are tilted and blurred. The model reads the photo into structured fields. A word search (no AI, `app/identify.py`) then shortlists 25 products the chain sells from the Kaggle product index, ordered by word match and closeness to the label price, and the model picks the one the label is for, asks (2 to 4 options) or says none. Price is used to rule products out, never as the only reason for "exact". A pick whose readable size differs by more than 10% from the label becomes a question. Dates with no year go to the nearest year, so a label that ended last week reads as ended.
- **Starting price links** (`scripts/link_classes.py`, run once, output committed). For each catalogue product and chain the model picks the product that is the same variant, tier and size within 10%, or none. Where a chain leaves the size out of the name (most Morrisons and Asda products), the size is worked out from the price per kg, litre or item and given to the model. Picks more than 10% off in size are dropped, and a multipack never matches a single bag. The same step runs in the background for each new class a scan starts (`link_other_chains` in `app/classes.py`). Without a key, rules pick instead and each link says which.

The route planning is plain optimisation (`app/planner.py`), not AI. The barcode lookup (`app/scan.py`) is a lookup plus rules, not AI: own-label detection reads the brand field.

Remove the AI and shelf label photos cannot be read, own-label products are mapped to the wrong brand, and lists are misread. See the numbers below.

## Results vs baseline

Baseline: fuzzy string matching for lists, and regexes plus word search for shelf labels (`app/baseline.py`). The fuzzy cutoff was tuned on a tuning set (the old receipt tuning lines, now in git history only), never on a test set.

| Task | Test set | Baseline | Claude Haiku 5.5 (our model) | Claude Opus 5.5, for comparison |
|---|---|---|---|---|
| List item to product group and brand | 45 items | 77.8% (35/45) | **100% (45/45)** | 97.8% (44/45), older prompt |
| Scanned product to product class | 101 real products, 42 with a class | 81.2% (82/101), 6 wrong merges, 13 of 42 matches missed | **87.1% (88/101)**, 2 wrong merges, 11 of 42 missed | 98.0% (99/101), 1 wrong merge, older prompt and labels |
| Shelf label to product and prices | 46 synthetic label photos, 5 chains, 6 products not in the list | 87.0% (40/46) product offered, asks on all 46, every price right 46/46, **given the label text typed perfectly** | **100% (46/46)** product offered, first option right 100%, asks on 2, 0 confident wrong, every price right 46/46, from the photo | not run |

Runs, all 17 Oct 2026 (`data/eval/results.json`, models as recorded in the file): Haiku 5.5 and the baseline at 23:25 BST, Opus 5.5 at 14:41 BST.

What changed for the 23:25 run: own label is split into value, standard and premium tiers, and the class answer now gives its reason before its choice. Before that, Haiku often wrote the right reason and then the wrong id ("matches the 6 eggs class" with the 12 egg class picked). Wrong merges fell from 10 to 2. A product class run just before, with the same prompts, scored 89.1% (90/101) with 0 wrong merges, so expect a point or two of noise. Two test labels changed with the tier split: Morrisons Savers bread now belongs in the value bread class, and Asda Just Essentials muesli has no class (the muesli class is standard own label). The list prompt also gained sizes and swaps; its score is on the same 45 items.

Before that, between the Opus run and an earlier Haiku run (21:28 BST), the list prompt changed: an item with no variant ("bread", "crisps") now matches every product it could mean and the planner picks the cheapest, instead of asking "which one?". The test set changed with it ("crisps" now expects both crisp groups). The other prompts did not change. Haiku costs about a fortieth of Opus per token ($0.10 / $0.50 per million input / output tokens, against $4 / $20). The cost of Haiku showed most in product class: 10 wrong merges against Opus's 1 before the reason-first change, 2 after. One run each, so treat the numbers as indicative.

The baseline moved from 78.2% to 81.2% on product class with the tier split: its rules no longer put value packs with standard own label.

- Product class: Haiku's 2 wrong merges are Lidl reduced fat beef mince put with 5% fat mince (a real error) and Yorkshire Tea for Hard Water put with Yorkshire Tea 80 (disputed: labelled "no class"). Its 11 misses are all the safe kind: it starts a new class rather than merge, mostly for sub-brands it does not know (Dairy Manor, Choco Nussa, Ashfields, Simply). The team must still check the labels.
- Shelf label: the photos are rendered by `scripts/make_labels.py`, clean and evenly lit. Real shelf photos (glare, angle, worn labels, several labels in frame) will score lower. Treat 100% as an upper bound until real photos are tested. The answers are known by construction, nobody labelled them. The baseline's 6 misses are the 6 made-up products: word search always offers something.

Baseline figures moved on 17 Oct 2026 after a tie-break fix: "milk" scored the same against semi-skimmed milk and Cadbury Dairy Milk, and catalogue order picked the chocolate. Ties now go to own label. List matching before the fix: 75.6%.

Product class baseline: the catalogue rules in `app/offmap.py`, else a class member with the same Open Food Facts category, size within 10% and the same brand (any own label counts as one). Its misses are Lidl and Aldi sub-brands missing from our brand list (Dairy Manor, Woodcote, Choco Nussa) and odd categories. Its wrong merges are premium and organic packs put with standard own label. A wrong merge is the costly error: two different products priced as one. The test products are real (Open Food Facts, ODbL); the answers were labelled by Claude Code under the rules in the prompt and **still need checking by the team**. The labeller and the model under test are both Claude, so until the team checks the labels the product class figures can be off either way. The 12 tuning products are the prompt's examples and are not in the test set. Brand names that appear only in the test set are kept out of the prompt.

The shelf label task measures the read (shelf, member, was price, multibuy, end date) and the product pick together, and also counts confident wrong picks (the model says "exact" and is wrong) and how many questions the shopper is asked. The label prompts have no examples, so there is no tuning split.

Run: `.venv/bin/python scripts/eval.py`. Results and every error are written to `data/eval/results.json`. A failed AI call is never replaced by the baseline: the task is reported as failed, or for product class the item counts as wrong and the failure count is printed.

The list test set is **synthetic**, written by the team with AI help in the style of UK shopping lists. The list prompt has no examples. Small sets: treat the numbers as indicative.

## Known limits

- **Starting prices are 2024 online prices.** Prices have risen since, and shops, Express stores especially, can charge more than the website. They are tagged with their month everywhere they appear. They have no member prices or offers: those come only from shelf labels.
- **Starting price links were made by the AI and are not yet checked by the team** (`data/kaggle/class_links.json`, `by: ai`). 195 of 380 class and chain pairs are linked (76 classes, 5 chains): Sainsbury's 48, Tesco 46, Morrisons 38, Asda 35, Aldi 28. Many value classes have no value product at a chain, which is expected. Rebuilt on 17 Oct 2026 when value own label was split from standard: links that were wrong on size (Morrisons Anchor 200g for 250g, Coca-Cola 1L for 2L) were dropped, and a link run with no AI picks rules instead. One suspect link: Tesco "Golden Granulated Sugar 1kg" for plain granulated sugar. Set `by` to `team` on links you check.
- A shelf label is compared across shops only when its product is one of the linked catalogue products. Other labels are saved and shown in "Your products" but not used in plans yet.
- Lidl, Co-op, Iceland and M&S have no product list, so their labels are saved under the name on the label and not compared.
- Multibuys count only for one product ("3 for £5" on the same item), not mixed "any 3" deals across products.
- `scripts/seed_db.py` now builds an empty database by default. `--synthetic` adds invented shelf label prices, which outrank starting prices at the shops they cover.
- The catalogue has 76 products: 46 product types, and a value range sibling for each standard own label one. Anything else shows as "not tracked" until a scan adds it.
- With no amount given, an item takes the cheapest pack of any size it matches, so "pasta sauce" can pick a 190g pot over a 500g jar. Write the amount to compare like with like.
- Matching a shelf label to an exact product covers Asda, Aldi, Morrisons, Sainsbury's and Tesco only (82,414 grocery products). The index is not updated after 13 Apr 2024, so products launched since then are missing. Its prices are shown only as dated starting prices. Current prices come from shelf labels and scans.
- A branch with no shopper price borrows the latest price from another branch of the same chain and format. Flagged in the UI. Express and big stores are kept apart.
- Travel distance is street distance over the OpenStreetMap walking, cycling or road network as of 17 Oct 2026, routed on our server (`app/streets.py`). Routes avoid car park aisles, driveways and back lanes unless a cut through is clearly shorter (they count 1.2 to 2 times their length when choosing), but the distance shown is the real length. The walk home retraces the walk out. Time is that distance at a fixed average speed per mode, not live traffic or bus timetables. Bus uses road distance. A point more than 400 m from any mapped street (outside Southampton) falls back to straight-line distance times 1.3, and the plan says so.
- Outlier prices (under 0.4x or over 2.5x the median) are saved but not used until confirmed.
- Shop list is OpenStreetMap as of 16 Oct 2026. Missing or closed shops are not corrected.
- Shelf label photos are converted to JPEG in the browser when the browser can open them (Safari can), else rejected with a message.
- Barcode lookup needs Open Food Facts to know the product. Unknown barcodes ask the shopper for the name. Its names and sizes are crowd-sourced and sometimes wrong, which is why the shopper confirms each one.
- A new class gets starting prices at the other chains only where the AI finds the same product in that chain's 2024 list. Classes started before 17 Oct 2026 on the hosted server need `scripts/link_scanned.py` run once. New classes start from Open Food Facts data, so their names can be rough, and they have no allergen tags: plans show "no allergen data" for them.
- One shopper pressing "Not the same?" keeps that barcode out of comparison for everyone. There are no accounts, so one person could also flood confirmations or prices. Fine for a demo, needs rate limits and per-user counts before launch.
- Saved products live in the browser's storage on that device only.
- Household: there are no accounts. A member is a nickname plus a random token stored on their device, so clearing the browser loses the place in the household (rejoin with the code). Anyone with the join code can join as a member, and an admin can remove them. The shared list and nicknames are stored on our server, which is the one place the app keeps anything a user typed about their home. Up to 12 members and 200 open items.
- Without an API key the app falls back to the baseline and says so on every screen.
- Open Food Facts has about 2,000 UK prices, mostly from Cardiff and London, and only a fraction map to our catalogue. They are chain-level prices from other towns, used only where no shopper price covers a shop, and labelled as such. Promotional prices are ignored, member prices are kept.
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

Refresh shop locations: `.venv/bin/python scripts/fetch_stores.py`. Refresh the street network: `.venv/bin/python scripts/fetch_streets.py`.

## Hosted server

Live at **https://nostobon-soton.fly.dev** (Fly.io, London, app `nostobon-soton`). Phones reach it over mobile data, no laptop or cable.

Moved on 18 Oct 2026 from `nostobon.fly.dev`, whose Fly trial ended. The new server started from the committed `data/` files: shopper data saved on the old server did not carry over. APKs built against the old address need `npm run phone:live` again.

- One machine, always on. The database is SQLite on a Fly volume (`/data/app.db`, set by `NOSTOBON_DB` in `fly.toml`). On first boot `db.init` builds it from the committed `data/` files, with no shopper prices. Every label, scan, trip and household change saved from any phone goes into it and survives deploys and restarts.
- Keep it to one machine: `app/db.py` shares one SQLite connection, so two machines would each have their own database. Always deploy with `--ha=false`.
- The API key is a Fly secret, never in the image.
- The site is public, so anyone with the address can make it call Claude. Set a spend limit on the Anthropic key.

Deploy what is on your branch (needs `flyctl` and access to the Fly app):

```bash
fly deploy --ha=false                       # build and replace the running server, the database is kept
fly secrets set ANTHROPIC_API_KEY=...       # once, or to change the key
fly logs                                    # server output
fly ssh console -C "sqlite3 /data/app.db"   # look at the live database
fly ssh sftp get /data/app.db app-live.db   # copy it down
```

Web changes reach the hosted app only after `fly deploy`. Deploy from `main`, so the live app is what is merged.

## Android app

`mobile/` is a Capacitor shell. It loads the web app from a server, so there is one codebase: edit `app/static/` and reopen the app (or swipe it away and back) to see the change. No rebuild.

Needs: Node, Android SDK, JDK 21 (in `~/.jdks` or `JAVA_HOME`), phone with USB debugging on. USB is only needed to install.

```bash
cd mobile && npm install
npm run phone:live # build APK against https://nostobon-soton.fly.dev and install over USB. Then unplug: it works on mobile data
npm run phone      # dev build against the laptop: localhost:8000 over USB, port forwarded
npm run reverse    # dev build, after replugging the phone: phone's localhost:8000 -> laptop
```

The dev build needs the server running on the laptop (`uvicorn app.main:app --reload`). If the server is not reachable either build shows an offline page, not a blank screen.

iPhone, or no APK: open https://nostobon-soton.fly.dev in the browser. The camera works because it is HTTPS.

Rebuild only when something native changes:

- **Server address.** `NOSTOBON_URL=https://... npm run phone` points the app at any server. `phone:live` sets it to the hosted one.
- **Logo.** Edit `app/static/icons/icon.svg`, then `npm run icons` and rebuild. Launcher, round, themed (monochrome) icons and splash are all built from that file.
- **Permissions or native plugins.** `mobile/android/app/src/main/AndroidManifest.xml`, `npm install @capacitor/<plugin>`.

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
- Generated with Claude Code on 17 Oct 2026: the UI redesign in `app/static/` (bottom tab bar, Geist font from Google Fonts, restyled screens, shorter copy, data sources and planning assumptions moved into fold-out sections).
- Generated with Claude Code on 17 Oct 2026: the Household tab (`app/household.py`, the household tables in `app/db.py`, the Household screen in `app/static/`), then the Invite button, adding saved products to the shared list, and faster refresh between phones, then owner, admin and member roles in place of adults and children, and a confirm step on every removal.
- Generated with Claude Code on 17 Oct 2026: "Buy again" chips under both add boxes (the buy-again section and household add queue in `app/static/app.js`, its styles in `app/static/style.css`).
- Generated with Claude Code on 17 Oct 2026: licence notices (`data/NOTICE.md`, `data/off/NOTICE.md`, the updated `data/kaggle/NOTICE.md`), the footer credits and the contribution note on the Scan screen.
- Generated with Claude Code on 17 Oct 2026: hosting on Fly.io (`Dockerfile`, `.dockerignore`, `fly.toml`, `requirements-server.txt`, the `phone:live` script, the hosted server section above).
- Generated with Claude Code on 17 Oct 2026: choosing which household items go on your list (tagged "household"), claims ("Shaheer is getting this", `claimed_by` on household items), the confirm-the-shop screen and `/api/trips` for corrected prices.
- Generated with Claude Code on 17 Oct 2026: shelf labels give their product a class so lists can find it (`assign_chain_product` in `app/classes.py`, `scripts/classify_labels.py`), adding prices for unpriced items on the confirm shop page, the list locked while a plan runs, and clearer location errors.
- Generated with Claude Code on 17 Oct 2026: vague list items ("bread") priced as the cheapest matching product instead of asking which one (list prompt and fallback in `app/ai.py`, list eval scoring in `scripts/eval.py`), and the Scan screen shop picker (search by shop, road, area or postcode, "Near me", nearest shops first).
- Generated with Claude Code on 17 Oct 2026: own label split into value, standard and premium tiers (`own_label_tier` in `app/scan.py`, the class and link prompts in `app/ai.py`, the value siblings in `data/catalogue.json`, the rebuilt `data/kaggle/class_links.json`, relabelled value items in the product class sets), sizes in lists (`fit_sizes` in `app/planner.py`), close swaps, background linking of new classes at every chain (`link_other_chains` in `app/classes.py`, `scripts/link_scanned.py`), pack sizes from unit prices, and the "quicker route is missing" note on the plan.
- Pre-existing work: none. Repo created after hacking opened on Fri 16 Oct 2026 20:00.
- Outside help: none yet.

## Team docs

Briefs, judging rules and planning live in [`docs/`](docs/). Start with [docs/event.md](docs/event.md).
- Generated with Claude Code on 17 Oct 2026: street routing in the planner (own router over OpenStreetMap streets in `app/streets.py` and `scripts/fetch_streets.py`, replacing the OSRM public servers, with a visible straight-line fallback), the street path on the route map, the Google Maps directions link and the OpenFreeMap base map in `app/static/`.
- Generated with Claude Code on 18 Oct 2026: trips that start from where the shopper is now (the start choice on the list screen, start and finish points in `app/planner.py` and `/api/plan`, the trip line, route, map and directions on the plan).
- Generated with Claude Code on 18 Oct 2026: the move to the `nostobon-soton` Fly app (`fly.toml`, `mobile/package.json`, the hosted server section above).
