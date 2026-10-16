# Track brief: FinTech

Source: `source-pdfs/fintech-brief.pdf`. In collaboration with JPMorganChase, Deutsche Bank and TrueMoney.

## The challenge

Build an AI-powered product that solves a real problem for someone who saves, spends, sends or manages money, and that you could realistically put in front of that person after the weekend. Banks, fintechs and wallet providers spend heavily on fraud, compliance and payments operations. Small businesses, migrant workers and vulnerable customers are still poorly served. No fixed project list: choose the problem, show it matters in finance.

Judges look past technical ambition: clear user, working core, plausible way to be paid. A simple tool one fraud team or one group of customers would use next month beats an impressive prototype nobody adopts.

**One-sentence test:**

> We help [a specific person] to [do or decide something] in [part of finance] using [AI and the data behind it].

Example: *We help remittance users stop scam payments before they leave by spotting the warning signs in the messages that prompted them.*

## Who to build for

One main user, designed, tested and pitched from their point of view:

- **Customer:** migrant worker sending money home, student, older person, someone recovering from a scam.
- **Bank or fintech employee:** fraud, payments operations, compliance and KYC, trade finance, customer services.
- **Small business or sole trader.**
- **Wallet agent or kiosk operator.**

Working well for one kind of customer, one team or one kind of payment is enough, and usually stronger.

**Fits:** scams and fraud, money laundering, cross-border payments and remittance, payment data, trade and business verification, small-business cash flow, regulation and compliance, digital money.

**Does not fit:**

- a general finance chatbot, or a trading bot or price prediction that does not lead to a decision;
- an existing product with an AI feature bolted on;
- anything needing real customer data, live bank credentials or moving real money (unless an organiser agrees in advance).

One track per team. If the idea also fits Southampton City or Responsible AI, pick where user and business case are strongest.

## What every project must show

- **A real financial problem.** Who has it, how often, what they do today. Backed by published data, a regulation or a conversation with someone affected.
- **AI the product depends on.** Remove the AI: if it still does its main job, rethink. If the AI classifies, predicts or extracts, compare against a simple baseline.
- **Works on real data.** Main task completable live, end to end, on public or openly licensed data with source and date visible. Real customer data is off limits. Synthetic data is fine for testing and anything personal, labelled as synthetic.
- **A business case.** Who pays (bank, fintech, wallet provider, businesses, customers), rough cost per user including AI, what it takes to work for a second bank or market.
- **Honesty about limits.** Show what it does not know, how old its data is, what happens with missing data, stale sources or out-of-scope input. **Show at least one failure case in the demo.**

## Directions they want to see

Optional. Original ideas are judged on the same terms. Following an example earns no extra credit.

1. **Scam check for people sending money home.** Migrant workers are prime targets, including deepfake "relative in distress" calls. UK reimbursement rules do not cover international payments. Tool reads the message or call behind a transfer, spots warning signs, warns before money leaves. Customer: wallet or remittance provider (each prevented scam saves a refund, a complaint, a lost user). Baseline: keyword list. Data: published scam scripts, public scam reports.
2. **Shell-company check for business onboarding.** Fraudsters open business accounts via shell companies with fake directors and mass-registration addresses. Tool takes a new business customer's details, pulls the Companies House record and director network, explains risk signals found. Customer: banks and fintechs opening business accounts; every UK lender runs the same checks. Data: Companies House free API and bulk data.
3. **Payment address fixer.** Swift is moving cross-border payments to structured addresses and will stop accepting free-text addresses once timing is agreed. Many banks hold messy free-text addresses. Tool cleans and structures them, flags uncertain ones, explains why. Customer: transaction banks, every bank on Swift worldwide. Baseline: pattern-matching rules. Data: OpenStreetMap.
4. **Trade document checker.** Before paying under a letter of credit, staff hand-check that invoice, bill of lading and other documents match each other and the credit's terms. Tool reads documents, extracts key fields, lists every discrepancy, catches forged or reused documents. Customer: banks with trade finance, licensed per document. Data: public sample trade documents, generated sets with planted errors.

## Data

No compulsory dataset. Check early that sources cover your market and you are allowed to use them. Any permitted source is fine if credited.

| Source | What it offers | Access and limits |
|---|---|---|
| Companies House API and bulk data | UK company records, officers, registered addresses, filing history, PSCs | Free; API needs a key. Bulk files are large, take a slice |
| UK sanctions list (OFSI / FCDO) | Names, aliases, identifiers of sanctioned people and entities | Free download; good for name matching and screening |
| World Bank Remittance Prices Worldwide | Cost of sending money between country pairs, by provider type | Free download; quarterly, not live |
| Bank of England and ECB exchange rates | Daily reference FX rates | Free; historical reference rates, not live trading rates |
| FCA Register and FCA / BoE publications | Authorised firms, warnings about unauthorised firms, policy statements, consultations | Public pages and downloads; check terms before bulk collection |
| PaySim (Kaggle) | Synthetic mobile-money transactions with fraud labels | Open; widely used, so originality must come from the product |
| IBM AMLworld (Kaggle) | Synthetic transactions with labelled laundering patterns | Open; large, sample it |
| Elliptic dataset (Kaggle) | Bitcoin transaction graph, licit/illicit labels | Open; check the licence |
| Public blockchain explorers (Etherscan, Basescan) | On-chain transfers incl. stablecoins and deposit tokens | Free tiers need a key, rate limited |
| OpenStreetMap | Structured address data | ODbL; credit OpenStreetMap contributors |

Keep API keys and passwords out of the repo.

## Track rules

Event-wide rules apply (teams of four, hacking Fri 20:00 to Sun 13:00, you own what you build). Plus:

- Build during the event; create the repo after hacking opens. Open-source libraries, templates and pre-trained models are fine. Your own earlier projects are not.
- README states which parts were AI-generated, what existed before the event and who helped.
- Show where each number comes from and when it was collected. Never present cached data as live or synthetic as real.
- No real customer data, no real bank account, card or wallet connection, never move real money. Build tools that detect scams and fraud, not tools that create deepfakes, scam scripts or fake documents.
- If the product touches investment, credit or borrowing, link to official guidance (FCA, MoneyHelper) instead of giving advice.

## Track-specific pitch questions

The pitch must answer clearly:

1. What evidence shows the problem is real and costly?
2. Who would deploy and pay for the product?
3. What would it take to roll it out to a second bank or market?

README must list every data source with its date and licence.
