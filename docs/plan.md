# Plan

## Team

| Person | GitHub | Role |
|---|---|---|
| Shaheer | ShaheerSA1 | |
| Nicolas | nicolito373 | |
| Kavian | k-jvn | |
| Suhayb | suhayb2 | |

Roles decided in person.

## Timeline

| When | Milestone |
|---|---|
| Fri 22:30 | Idea and track decided. One-sentence test written in [ideas.md](ideas.md#decision) |
| Fri night | Repo skeleton, data access confirmed (keys, downloads), thinnest possible end-to-end path |
| Sat 12:00 | Core task runs end to end on real data, even if ugly |
| **Sat 18:00** | **Core task solid end to end (organisers' own advice)** |
| Sat night | Baseline vs AI numbers, test set results, failure case built into the UI |
| Sun 09:00 | Feature freeze. Only fixes from here |
| Sun 10:00 | Record demo video |
| Sun 11:30 | Video on YouTube, summary written, README complete, repo public |
| Sun 12:30 | Submitted. Buffer until 13:00 lock |

## Build order (barcode first, agreed 17 Oct 2026)

1. [x] Barcode scan, Open Food Facts lookup, photo confirm, saved products (`app/scan.py`, Scan screen)
2. [ ] Shelf-label photo to price and member price, with eval on the Saturday label photos (about 40: tune 10, test 30)
3. [x] Cross-chain own-label matching into product classes, with baseline and eval (`app/classes.py`, eval task 4). AI numbers need the API key
4. [x] Loyalty flags in the planner: member prices count only for cards in the profile, and the plan shows the shelf price struck through with the scheme named (`app/planner.py` `effective_price`). Dummy housemate accounts later, labelled synthetic

Saturday shop: each of us photographs about 10 shelf labels across Tesco, Sainsbury's, Lidl and Co-op, and scans the same products. Label the photos by hand.

## Submission checklist

- [ ] Demo video, 1:00 to 3:00, real product on screen, uploaded to YouTube (public or unlisted)
- [ ] Pitch format chosen (full video, or shorter video plus live pitch) and video length given
- [ ] Summary, 150 words max: user and problem, why it matters, solution, how it scales
- [ ] Repo is **public**
- [ ] README: setup / run instructions
- [ ] README: every data source with date and licence ([data-sources.md](data-sources.md))
- [ ] README: what the AI does
- [ ] README: what was AI-generated, what existed before, who helped
- [ ] README: test results vs baseline, with sample sizes
- [ ] README: known limits
- [ ] No secrets in git history
- [ ] Live link (optional)

## Pitch checklist

- [ ] Opens with the user and one piece of evidence (0:00-0:20)
- [ ] Demo of the full core task (0:20-1:40), in the video
- [ ] Why AI, with baseline numbers (1:40-2:10)
- [ ] Who pays, cost per user, how it grows, first three customers (2:10-2:45)
- [ ] One failure shown, what we would build next (2:45-3:00)
- [ ] Track's three questions answered (see the brief)
- [ ] A quote from a real potential user
- [ ] Stage 2 rehearsal: someone feeds the product a surprise input, 2-minute live demo, then 5 minutes of hard questions
