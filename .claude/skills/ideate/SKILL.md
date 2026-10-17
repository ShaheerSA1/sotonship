---
name: ideate
description: Generate, filter and stress-test niche SotonShip idea candidates that can win the hackathon and keep going as a real product afterwards. Use when asked for new ideas, a fresh brainstorm, or to evaluate an idea for SotonShip.
---

# Ideate

Goal: a few niche ideas that score high on the five criteria, survive a live judge input, and are worth running as a product after Sun 18 Oct.

## 1. Load context first

Read these, nothing else from the repo:

- `docs/judging.md`: criteria, weights, track lenses, Stage 1 crowd vote, Stage 2 live input
- `docs/briefs/*.md`: the three tracks
- `docs/ideas.md`: ideas 1 to 12 already exist. Do not repeat them or lightly reskin them.

## 2. Generate from sources of real pain, not from thin air

Paul Graham's test for a good idea: the founders want it, can build it, and few others see it is worth doing. Two rules follow from it:

- **Turn off the schlep and unsexy filters.** Tedious, boring, paperwork-heavy problems are where other teams will not go. That is the niche.
- **Avoid tarpit ideas.** Ideas that feel good because everyone has thought of them (generic chatbot, study planner, budgeting app, "AI assistant for X"). If three other teams in the room could pitch it, drop it.

Use at least four of these lenses. Each lens must produce concrete candidates, each with a named user doing a named task.

1. **New rule, forced buyer.** A UK law, regulator rule or deadline that started in 2025 or 2026, or starts soon, makes someone do new paperwork or checks. Search for it. Forced buyers pay.
2. **The spreadsheet job.** Someone reads PDFs, emails or forms all day and types results into a spreadsheet. Search job ads for the task ("review", "triage", "reconcile", "check against"). That job is the product.
3. **Unwrapped public data.** A public dataset or register that is free but painful to use, where the hard part is reading unstructured text. Companies House, FCA register, council planning portals, court judgments, FOI responses, Hansard, procurement notices.
4. **Change the user of a crowded idea.** Take a brief example or an incumbent product and serve the user it ignores (too small, too poor, too local). Ask why incumbents skip them and whether that reason is real.
5. **Why now.** What can models do in 2026 that was not possible two years ago: read long documents, read photos and scans, reason over tables, run cheap at volume. Find a job that only became automatable this year.
6. **Complaint mining.** Search Reddit, MoneySavingExpert, Trustpilot, Mumsnet, student forums for repeated angry posts about one task. Quote them (short, attributed).
7. **Our own edge.** What the four of us know or can reach that other teams cannot: Southampton, student life, part-time jobs, family businesses, courses. Founder fit is what keeps a project alive after the event.

8. **Analogy.** A business model proven in one industry or country, moved to a UK vertical that lacks it. Name the original and why it transfers.
9. **Reverse brainstorm.** Ask "how would we make this user's week worse?" for a chosen user, then invert each answer into a product.

### Where to search

These sources show who is already paying, or legally must pay, for a problem:

- **legislation.gov.uk, gov.uk consultations and guidance:** rules with commencement dates. Example signal: the Renters' Rights Act 2025 phases in a landlord database and a landlord ombudsman around late 2026 (secondary sources, confirm on gov.uk).
- **FCA policy statements and Dear CEO letters:** what regulated firms are being told to fix.
- **Find a Tender and Contracts Finder:** what councils and public bodies actually buy, with prices.
- **Innovate UK and SBRI competitions:** problems the government will fund someone to solve.
- **Ombudsman decisions** (Financial, Housing, Local Government): repeated complaint types with real case text.
- **Southampton City Council committee papers:** local problems with numbers, written by officers.
- **YC Requests for Startups** (ycombinator.com/rfs): what investors think is under-served. Use for "why now", not as a list to copy.

Use WebSearch to back every claim about a rule, a number or a market. Cite source and date. Flag anything unverified.

## 3. Kill fast

Drop a candidate if any of these is true. Say which rule killed it.

- Rules, a form or a lookup do the core job (fails "remove the AI").
- Needs real personal or customer data to work or to demo.
- A judge cannot hand it an arbitrary input on the spot.
- The core task cannot run end to end by Sat 18:00 with four people.
- An incumbent already serves the same user well and cheaply.
- Data access needs a partnership or paid licence we cannot get this weekend.
- FinTech: it generates scam material, moves money, or gives personal investment advice.

## 4. Afterlife test

For survivors, answer each in one line. This is what makes it worth continuing.

- **First three customers:** names or exact types, and how we reach them without the hackathon.
- **Price and cost:** what one customer pays per month, what one use costs in inference.
- **Wedge:** the narrow first task, and the next two tasks it expands into.
- **Moat that compounds:** labelled data, eval set, integrations or trust that grows with use.
- **Second market:** next city, next regulator, next industry.
- **Builder fit:** which of us would want to work on this for a year.

## 5. Stress test the top 3

- **Live-input attack:** list five nasty inputs a judge could give (off-topic, edge case, adversarial, missing data, different language). Say what the product does with each.
- **Baseline:** the simple rule or keyword method we would compare against, and the metric.
- **Pre-mortem:** it is Sunday 14:00 and we lost. Give the three most likely reasons.
- **Crowd test:** can a first-year student understand the user and the pain in ten seconds? Stage 1 is 70% public vote.

- **Riskiest assumption:** the one belief that kills the idea if false, and the cheapest test we can run this weekend.

Installed pm-skills plugins to use here: `identify-assumptions-new` and `prioritize-assumptions` (pm-product-discovery), `pre-mortem` and `strategy-red-team` (pm-execution), `market-sizing` and `competitor-analysis` (pm-market-research), `beachhead-segment` (pm-go-to-market), `lean-canvas` and `value-proposition` (pm-product-strategy). If the `venture`, `strategy-frameworks` or `venture-capital-intelligence` plugins are enabled, also use their devil's advocate, JTBD, Blue Ocean and startup-screening skills.

## 6. Validate with a real person this weekend

Organisers reward quoting a real potential user. For the top pick, write a five-question interview using Mom Test rules:

- Ask about their life and the last time the problem happened, not about our idea.
- Ask about past behaviour ("talk me through the last time", "what have you tried", "what did it cost you"), never "would you use this".
- Listen more than talk. If they have never looked for a fix, they will not buy ours.

Name who at the event could answer it (mentors, partner bank staff, council staff, other students).

## 7. Output

Append to `docs/ideas.md` under a new heading, numbering from 13, in the same format as ideas 1 to 12: one-sentence pitch, user, buyer, AI core, baseline, data, live input, risks, crowd appeal. Add a score table using the template there, plus two columns: **Afterlife** (1 to 10) and **Niche** (1 to 10, how few teams will build it). Then name the top pick and why, in under 100 words.

Log any data source found in `docs/data-sources.md`. Follow the writing rules in `CLAUDE.md`: short, firm, no em or en dashes.
