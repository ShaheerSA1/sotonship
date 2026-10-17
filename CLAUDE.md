# SotonShip 2026

Hackathon entry. Team of four: Shaheer, Nicolas, Kavian, Suhayb.
Hacking: Fri 16 Oct 20:00 to **Sun 18 Oct 13:00 BST, hard lock**. Goal: win.

## Read these instead of the PDFs

The briefs are converted to markdown. Do not re-read `source-pdfs/` unless a markdown file is missing something.

- [docs/event.md](docs/event.md): times, tracks, event-wide rules, deliverables
- [docs/judging.md](docs/judging.md): the five criteria, weights, pitch structure, VC for a Day, Stage 2 panel
- [docs/briefs/fintech.md](docs/briefs/fintech.md)
- [docs/briefs/southampton-city.md](docs/briefs/southampton-city.md)
- [docs/briefs/responsible-ai.md](docs/briefs/responsible-ai.md)
- [docs/ideas.md](docs/ideas.md): the chosen idea (Nostobon), its evaluation and the decision
- [docs/plan.md](docs/plan.md): team lanes, timeline, submission and pitch checklists
- [docs/data-sources.md](docs/data-sources.md): log of every data source

## Current phase

**Building the Nostobon MVP** (shopper-scanned shelf prices, see `docs/ideas.md`). Track: **Southampton City**. Model: Claude Haiku 5.5. Receipts were dropped on 17 Oct 2026. Code in `app/`, setup in `README.md`.

## How judging works (short version)

Score = 0.20 Problem and user + 0.20 AI at the core + **0.25 Working product** + 0.20 Business and scale + 0.15 Responsibility and trust.
Stage 1 is 70% public vote, 30% judges. Top 3 per track reach a panel that feeds the product **one live input of its own choosing**.
Every decision should be tested against: does this raise one of those five scores, or does it help us survive a surprise live input?

## Rules that constrain the code

These are competition rules. Breaking one can cost the entry.

- **Never commit secrets.** API keys go in `.env` (gitignored). Add the key name to `.env.example`.
- **No real customer data, no real personal data, no real bank accounts, never move money.** Synthetic data is fine, labelled as synthetic in the UI and in the data.
- **Every number shown in the product or pitch shows its source and date.** Never present cached data as live or synthetic as real.
- **Log every data source** in `docs/data-sources.md` with URL, licence and date collected, when you add it.
- **The AI must be the core.** Always keep a simple baseline (rules, keywords, regex) alongside it and an eval script that compares the two on a held-out test set. Keep tuning examples separate from test cases. Report sample sizes.
- **Failure must be visible.** The product shows when it does not know, when data is missing or stale, or when input is out of scope. Never hide errors behind a generic message.
- **No own earlier projects.** Everything is built during the event. Open-source libraries, templates and pre-trained models are fine.
- **AI-generated code must be disclosed.** Claude is writing code in this repo. Keep the "AI disclosure" section of `README.md` accurate as work happens.
- Do not send confidential or non-public information to external AI services.
- Southampton City: the main task must run on genuine Southampton data, with source and date visible. Do not collect personal data we do not need. Do not send non-public council information to an external AI service. Safety, health or emergency topics link to official guidance.

## Working style

- Time is the constraint. Prefer the simplest thing that works end to end over anything clever. Depth on one task beats breadth.
- Core task working end to end by Sat 18:00. Feature freeze Sun 09:00.
- Four people commit to this repo at once. Small commits, pull before push, work on branches for anything that might break `main`. `main` must always run.
- Write docs plainly: short sentences, no filler, no em or en dashes.
- Each track has extra judge questions ("track lenses") in `docs/judging.md`. We are in Southampton City: the product and pitch must answer its lens and its three pitch questions in `docs/briefs/southampton-city.md`.
