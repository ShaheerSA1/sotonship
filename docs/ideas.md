# Idea: Nostobon

The idea the team is building. MVP: see [README](../README.md).

## What actually wins here

Read from the rules, not guesswork:

- **Stage 1 is 70% public money.** The crowd is other participants and the public. A user they recognise and a demo they feel beats a clever B2B tool nobody in the room understands. You have to get through Stage 1 to reach the panel.
- **Stage 2 gives the panel one input of its own choosing, live.** The product must handle an arbitrary real input without breaking. Prefer ideas where the input is something a judge can produce on the spot (a message, a company name, an address, a photo) and the data behind it is live or public.
- **Working product is the biggest weight (25%).** Pick something the core of which runs end to end by Saturday evening.
- **"Remove the AI" test (20%).** If rules or a lookup do the main job, it fails C2. The AI must do the hard part, and we need a baseline it beats with numbers.
- **One failure shown on purpose.** Plan the failure case as a feature: "here is what it says when it does not know".
- **The example directions in the briefs will be crowded.** Following one earns nothing. If we pick one, our angle has to be sharper than the obvious version.

## Nostobon: shopper-scanned shelf prices (Southampton City)

Proposed by Shaheer, 17 Oct 2026. Working title was Basket.

> We help Southampton students cut their weekly grocery bill by pooling the shelf prices shoppers scan in local shops, and telling them which nearby shops to visit for their list, counting loyalty prices and the time the trip takes.

### Design changes, 17 Oct 2026

1. **Barcode first.** Receipts often print a vague name ("APPLES", "CHICKEN 4.30"), so the exact product cannot always be known. The barcode scan became the main way prices come in.
2. **Shelf labels, receipts dropped.** A photo of the shelf label gives the shelf price, member price, multibuy and offer end date in one go. Receipts were removed from the app, eval and data. The old receipt work is in git history.
3. **Track: Southampton City, not FinTech.** FinTech fit was the weak point (see the evaluation below): its partners and fits list are banks, fraud and payments. Southampton City wants a named local resident, genuine Southampton data and a council outcome, which this idea has.
4. **Model: Claude Haiku 5.5.** About a fortieth of Opus 5.5's price per token. See the README results for what that costs in accuracy.

How prices come in:

- **Shelf label photo.** The AI reads the label and picks the product from the chain's product list. The shopper checks every field before saving.
- **Scan.** The shopper scans the pack barcode. Open Food Facts gives the name, brand, size and photo. The shopper confirms with one tap, or types the name if it is wrong. Then the shelf price, and the member price (Clubcard, Nectar) if the label shows one. Both prices are kept, so people without the card still see the normal price.
- **Saved products.** Each confirmed product is kept on the device. Next trip the shopper only types the price.
- **Loose and weighed goods.** No barcode on the item. Prefix-2 codes are ones the shop prints itself and are treated as a hint, not an identity: the shopper types what it is. Loose produce is compared at category level (apples, per kg).
- **Loyalty cards** are set in the profile. The planner uses member prices only for cards the user has. Rules, not AI.

Where the AI goes, in order of value:

1. **Matching own label across chains.** Barcodes only match identical products, and own-label goods have a different barcode at every chain. Tesco fusilli 500g and Lidl Combino fusilli 500g share nothing a lookup can join, and own label is most of what students buy. The AI decides which products are the same thing (name, size, category, ingredients) and groups them into a product class. Spotting that a product is own label is a lookup on the brand field, not AI. Baseline: same Open Food Facts category and size within 10%.
2. **Reading shelf labels from a photo.** Price, member price, multibuy ("any 3 for £5"), unit price and end date in one photo, instead of typing. Baseline: regex on the typed label text. Still needs real photos from Southampton shops: tune on about 10, test on the rest.
3. **Free-text list to products.** Already built.

Price reports that look fake are caught by statistics (outlier check), not AI. Pitch that under trust.

- **User:** student doing a weekly shop in Portswood, Highfield, Shirley. Not "everyone who shops".
- **The route planner and the allergy filter are rules, not AI.** Do not pitch them as AI.
- **Results:** see the README. On 17 Oct 2026 Haiku 5.5 beat the baseline on all three tasks (list 91.1% vs 77.8%, product class 86.1% vs 78.2%, synthetic shelf labels 100% vs 87.0%), but made more wrong merges on product class than the baseline (12 vs 9). Opus 5.5 made 1.
- **Data:** OpenStreetMap shops in Southampton (real, ODbL). Shopper-scanned shelf prices are the main price source. Kaggle 2024 online prices are the dated starting price, and Open Food Facts Open Prices fills gaps. The demo needs real scans from Southampton shops: the brief asks for genuine Southampton data with source and date.
- **Live input:** strong. A judge types any list. Out-of-catalogue items show "not tracked".

Scoring: weighted = 0.20×C1 + 0.20×C2 + 0.25×C3 + 0.20×C4 + 0.15×C5, each 1 to 10.

### Evaluation

First written for the receipt design under FinTech. Updated for the changes above.

**Verdict: it will win crowd votes and demo well. The weak point is the payer (C4). FinTech fit was the other one, fixed by moving to Southampton City.**

What works:

- **Crowd appeal is very high.** Everyone in the room buys groceries and knows Lidl is cheaper than the Tesco Express next door. That is 70% of Stage 1.
- **In-store prices are the real differentiator.** Price comparison sites scrape online prices. Shelf labels give in-store prices, Express and Local formats, and member prices.
- **It handles a surprise live input** and fails visibly on items we do not track.

What is wrong or risky:

1. **Cold start.** A community database is empty on day one. Fix: all four of us scan shelf labels in three or four Portswood shops. That gives a real Southampton price set for the demo, and real photos for the label eval.
2. **No clear payer.** Shoppers will not pay much for this. Southampton City options: the council or student union (cost-of-living support, with a measured outcome such as pounds saved per household), and aggregated shop price data for councils, charities and researchers. Never sell personal data, and never let money change the rankings.
3. **FinTech fit was loose.** Fixed: the team moved to Southampton City.
4. **Drop video games and HMV.** Different products, prices already online (PriceSpy and similar), different trip logic. Depth beats breadth: groceries only.
5. **The saving has to be worth the walk.** If splitting a £25 shop saves £1.50 for 20 extra minutes, students will not bother. Get a published figure on the gap between the cheapest and dearest supermarket for the same basket (Which? publishes a monthly comparison, **check the current figure and date before quoting**).
6. **Competition.** Trolley.co.uk compares UK supermarket prices already (**check its current coverage of Lidl, Aldi and Express stores**). The answer to "why not Trolley?" has to be in-store and member prices from shelf labels.

Trust (C5), already in the MVP: the photo is never stored, digit runs (card and loyalty numbers) are stripped, there are no accounts, the shopper checks every field before saving, outlier prices are held back, and synthetic data is tagged everywhere.

Cost: Claude Haiku 5.5 is $0.10 and $0.50 per million input and output tokens. A label photo of about 1,600 image tokens, plus the prompt and the answer, costs well under a tenth of a penny. **Estimate, measure from usage logs.**

### Scores

| Idea | C1 | C2 | C3 | C4 | C5 | Weighted | Crowd | Live-input safe | Afterlife | Niche |
|---|---|---|---|---|---|---|---|---|---|---|
| Nostobon | 7 | 6 | 7 | 4 | 7 | 6.2 | Very high | Yes | 6 | 4 |

Scored for the receipt design under FinTech, not rescored since. C3 moves to 8 with real Southampton scans. C4 stays low until we can name a buyer.

### Before the pitch

1. Scan real shelf labels in Southampton shops and run the label eval on them.
2. Ask council or student union contacts at the event: would a measured cost-of-living saving be worth funding? Quote the answer.
3. Ask five students when they last shopped at two places to save money, and what it saved them.

## Decision

- **Chosen idea:** Nostobon
- **Track:** Southampton City (moved from FinTech, 17 Oct 2026)
- **One sentence:** see the quote above.
- **Decided by / when:** Shaheer, 17 Oct 2026. Barcode-first design agreed by the team, 17 Oct 2026. Receipts dropped, Haiku 5.5 and Southampton City chosen by the team, 17 Oct 2026.
