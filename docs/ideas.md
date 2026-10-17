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

## Nostobon: community receipt prices (FinTech)

Proposed by Shaheer, 17 Oct 2026. Working title was Basket.

> We help Southampton students cut their weekly grocery bill by pooling the shelf prices shoppers scan and the receipts they upload, and telling them which nearby shops to visit for their list, counting loyalty prices and the time the trip takes.

### Design change, 17 Oct 2026: barcode first

Receipts often print a vague name ("APPLES", "CHICKEN 4.30"), so the exact product cannot always be known. The team chose to make the barcode scan the main way prices come in. Receipts stay as a second input, since they already run and have eval numbers.

- **Scan.** The shopper scans the pack barcode in store. Open Food Facts gives the name, brand, size and photo. The shopper confirms with one tap, or types the name if it is wrong. Then they type the shelf price and the member price (Clubcard, Nectar) if the label shows one. Both prices are kept, so people without the card still see the normal price.
- **Saved products.** Each confirmed product is kept on the device. Next trip the shopper only types the price.
- **Loose and weighed goods.** No barcode on the item. Prefix-2 codes are ones the shop prints itself and are treated as a hint, not an identity: the shopper types what it is. Loose produce is compared at category level (apples, per kg).
- **Loyalty cards** are set in the profile. The planner uses member prices only for cards the user has. Rules, not AI.

Where the AI goes, in order of value:

1. **Matching own label across chains.** Barcodes only match identical products, and own-label goods have a different barcode at every chain. Tesco fusilli 500g and Lidl Combino fusilli 500g share nothing a lookup can join, and own label is most of what students buy. The AI decides which products are the same thing (name, size, category, ingredients) and groups them into a product class. Spotting that a product is own label is a lookup on the brand field, not AI. Baseline: same Open Food Facts category and size within 10%.
2. **Reading shelf labels from a photo.** Price, member price, multibuy ("any 3 for £5"), unit price and end date in one photo, instead of typing. Baseline: regex on OCR text. Test set: about 40 label photos from the Saturday shop, tune on 10, test on 30. If it does not clearly beat the baseline, manual entry stays.
3. **Free-text list to products.** Already built.
4. **Multibuy rules.** The AI turns promo text into a rule. The planner (rules) applies it.

Price reports that look fake are caught by statistics (outlier check), not AI. Pitch that under trust.

- **User:** student doing a weekly shop in Portswood, Highfield, Shirley. Not "everyone who shops".
- **AI core (receipt design, before the change above):** reading receipt photos and e-receipts (abbreviations, own-label names like Crusti Croc for Lidl, loyalty lines), and mapping a free-text list to products ("dairy milk" is chocolate, "oat milk" is not tracked). The route planner and the allergy filter are rules, not AI. Do not pitch them as AI.
- **Baseline:** regex parser plus fuzzy matching. 80.3% on 61 synthetic receipt lines, 77.8% on 45 synthetic list items, right product among 3 options on 18 of 30 synthetic exact product lines. AI not run yet. The AI has to beat these clearly or C2 collapses.
- **Data:** OpenStreetMap shops (real, ODbL). Community receipts are the main price source. Open Food Facts Open Prices fills gaps for now. Demo receipts are synthetic until real ones come in.
- **Live input:** strong. A judge types any list. Out-of-catalogue items show "not tracked".

Scoring: weighted = 0.20×C1 + 0.20×C2 + 0.25×C3 + 0.20×C4 + 0.15×C5, each 1 to 10.

### Evaluation

**Verdict: it will win crowd votes and demo well. The weak points are the payer (C4) and FinTech fit.**

What works:

- **Crowd appeal is very high.** Everyone in the room buys groceries and knows Lidl is cheaper than the Tesco Express next door. That is 70% of Stage 1.
- **The receipt angle is the real differentiator.** Price comparison sites scrape online prices. Receipts give in-store prices, Express and Local formats, and the loyalty price people actually paid. It is also the user's own data, so no scraping terms are broken.
- **It handles a surprise live input** and fails visibly on items we do not track.

What is wrong or risky:

1. **Cold start.** A community database is empty on day one. The demo runs on synthetic prices, and judges will discount that (C3 asks for real data). Fix: all four of us shop Saturday morning at three or four Portswood shops and upload 20+ real receipts. That gives a real Portswood price set for the demo.
2. **No clear payer.** Shoppers will not pay for this. Options, all with a catch:
   - A bank or fintech licenses it as a budgeting feature. JPMorganChase runs Chase UK in the UK. A bank's statement only shows "TESCO £23.40"; receipts add the item-level detail it does not have. Strongest FinTech story, unproven appetite.
   - Sell an anonymised item-level price index (the Fetch Rewards and NielsenIQ model). Real business, but it pulls against the privacy story.
   - Retailer promotions. Conflict of interest: the moment a shop pays, the "best plan" is no longer neutral.
3. **FinTech fit is loose.** The brief's fits list is fraud, AML, payments, remittance, small-business cash flow, compliance. Household spending fits only "someone who spends money". The partner-bank lens question ("could one of our partner banks adopt it?") needs the Chase UK answer above, said out loud. The idea fits Southampton City (cost of living, local shops, genuine Southampton data) at least as well.
4. **Drop video games and HMV.** Different products, prices already online (PriceSpy and similar), different trip logic. Depth beats breadth: groceries only.
5. **The saving has to be worth the walk.** If splitting a £25 shop saves £1.50 for 20 extra minutes, students will not bother. Get a published figure on the gap between the cheapest and dearest supermarket for the same basket (Which? publishes a monthly comparison, **check the current figure and date before quoting**).
6. **Competition.** Trolley.co.uk compares UK supermarket prices already (**check its current coverage of Lidl, Aldi and Express stores**). The answer to "why not Trolley?" has to be in-store and loyalty prices from receipts.

Trust (C5), already in the MVP: the photo is never stored, digit runs (card and loyalty numbers) are stripped, there are no accounts, the user checks every line before saving, outlier prices are held back, a receipt cannot be uploaded twice, and synthetic data is tagged everywhere.

Cost: one receipt is roughly 4k input and 1k output tokens. At Opus 5.5 list prices ($4 and $20 per million) that is about $0.04 a receipt before thinking tokens. **Estimate, measure from usage logs.** Running the eval on `claude-haiku-5-5` ($0.10 and $0.50) is the obvious cost test.

### Scores

| Idea | C1 | C2 | C3 | C4 | C5 | Weighted | Crowd | Live-input safe | Afterlife | Niche |
|---|---|---|---|---|---|---|---|---|---|---|
| Nostobon | 7 | 6 | 7 | 4 | 7 | 6.2 | Very high | Yes | 6 | 4 |

C2 moves to 7 or 8 if the AI clearly beats the baseline on the eval. C3 moves to 8 with real receipts. C4 stays low until we can name a buyer.

### Before committing to it

1. Get an API key into `.env` and run `scripts/eval.py`. If the AI does not beat 80.3%, 77.8% and 18/30 by a wide margin, the AI story is weak.
2. Ask a partner bank mentor directly: would item-level receipt data be worth anything to your app? Quote the answer.
3. Ask five students when they last shopped at two places to save money, and what it saved them.

## Decision

- **Chosen idea:** Nostobon
- **Track:** FinTech (proposed, Southampton City is the alternative)
- **One sentence:** see the quote above.
- **Decided by / when:** Shaheer, 17 Oct 2026. Barcode-first design agreed by the team, 17 Oct 2026.
