# Ideas

Brainstorm and shortlist. Add ideas at the bottom, score them, then pick one and record it in [decision](#decision).

## What actually wins here

Read from the rules, not guesswork:

- **Stage 1 is 70% public money.** The crowd is other participants and the public. A user they recognise and a demo they feel beats a clever B2B tool nobody in the room understands. You have to get through Stage 1 to reach the panel.
- **Stage 2 gives the panel one input of its own choosing, live.** The product must handle an arbitrary real input without breaking. Prefer ideas where the input is something a judge can produce on the spot (a message, a company name, an address, a photo) and the data behind it is live or public.
- **Working product is the biggest weight (25%).** Pick something the core of which runs end to end by Saturday evening.
- **"Remove the AI" test (20%).** If rules or a lookup do the main job, it fails C2. The AI must do the hard part, and we need a baseline it beats with numbers.
- **One failure shown on purpose.** Plan the failure case as a feature: "here is what it says when it does not know".
- **The example directions in the briefs will be crowded.** Following one earns nothing. If we pick one, our angle has to be sharper than the obvious version.

## Scoring template

Score 1 to 10 against the judging criteria, plus two practical columns.

| Idea | C1 Problem 20% | C2 AI 20% | C3 Works 25% | C4 Business 20% | C5 Trust 15% | Weighted | Crowd appeal | Live-input safe |
|---|---|---|---|---|---|---|---|---|

Weighted = 0.20×C1 + 0.20×C2 + 0.25×C3 + 0.20×C4 + 0.15×C5.

## Shortlist (first pass)

Scores are first-pass guesses to argue over, not facts.

### 1. Pay-safe: scam check before a bank transfer (FinTech)

> We help people about to send a bank transfer spot a scam before the money leaves, by reading the message, ad or call that prompted it and checking the payee against the FCA Register and Warning List.

- **User:** student or older person told to "move money" or "invest" by a message. Buyer: banks and payment providers, who now carry the cost of APP fraud reimbursement on UK domestic payments.
- **AI core:** LLM reads free-text messages and screenshots, extracts the claimed firm, the ask and the pressure tactics, matches against clone-firm patterns. Baseline: keyword list.
- **Data:** FCA Register and Warning List (public), public scam scripts and reports, synthetic labelled message set.
- **Live input:** judge pastes any message. Strong.
- **Risk:** close to the brief's example 1, so likely crowded. Differentiate on the FCA grounding and clone-firm detection.
- **Verify before pitching:** current PSR APP reimbursement rules and cap, UK Finance's latest APP fraud figure.

### 2. Shell-company check for business onboarding (FinTech)

- **User:** onboarding analyst at a bank or fintech. Buyer: every UK lender opening business accounts.
- **AI core:** needs care. Rules catch mass-registration addresses and serial directors. The AI has to do something rules cannot: e.g. compare stated business activity against SIC codes, filings and web presence, then explain the risk in plain words.
- **Data:** Companies House API (free key), bulk data slice, OFSI sanctions list.
- **Live input:** judge types any company number. Very strong, all real data.
- **Risk:** low crowd appeal. Fails C2 if it is just a rules engine.

### 3. Payment address fixer (FinTech)

- **User:** payments operations team at a transaction bank. Every bank on Swift has this problem.
- **AI core:** parse messy free-text addresses into structured fields, flag low-confidence ones with reasons. Baseline: regex rules. Easy to measure accuracy.
- **Data:** OpenStreetMap, synthetic messy addresses generated from real ones.
- **Live input:** judge types any address. Strong.
- **Risk:** very low crowd appeal. Judges from JPM and Deutsche Bank would love it; the public will not invest.

### 4. HMO licence pre-check for Southampton landlords (City)

- **User:** small landlord or letting agent before an HMO inspection. Buyer: agents, landlords, or the council.
- **AI core:** read property details and documents, check against published Southampton HMO licence conditions, list gaps.
- **Data:** SCC HMO licensing conditions (public).
- **Live input:** weaker. Judge needs a document to hand over.
- **Risk:** students in the crowd relate to bad HMOs, but the user is the landlord.

### 5. Street report triage (City)

- **User:** council street-scene officer. Buyer: the council, then every UK council.
- **AI core:** classify, merge duplicates, rank urgency, route. Baseline: keyword routing.
- **Data:** public FixMyStreet reports for Southampton.
- **Live input:** judge writes any report. Strong.
- **Risk:** obvious and likely crowded.

### 6. Support-bot release check (Responsible AI)

- **User:** team shipping a support chatbot. Buyer: SaaS company or support agency.
- **AI core:** faithfulness checks on RAG answers against approved sources, review queue.
- **Live input:** judge asks any question. Medium.
- **Risk:** developer tool, low crowd appeal.

## Our own ideas

Add here. Same format: one-sentence test, user, buyer, AI core, data, live input, risk.

## Decision

- **Chosen idea:**
- **Track:**
- **One sentence:**
- **Why this over the others:**
- **Decided by / when:**
