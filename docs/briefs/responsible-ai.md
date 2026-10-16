# Track brief: Responsible AI

Source: `source-pdfs/responsible-ai-brief.pdf`. Linked to RAi UK. Sources in the brief checked 15 Oct 2026.

## The challenge

Build a product that makes AI useful and trustworthy for a specific person, and pitch it as a business. Either a tool that helps others develop, test or govern AI, or an AI-powered product in any sector where responsible design is central to the value. No fixed problem, sector or technology.

A focused product one customer could trial after the weekend beats a broad promise to make all AI safe. **Responsibility should change what the product does, how it is tested or what its users can control.**

**One-sentence test:**

> We help [a specific person] to [do or decide something] using [AI or an AI assurance tool], while reducing [a specific risk to people].

Example: *We help customer-support teams test whether their AI answers are supported by approved sources before a chatbot update reaches customers.*

## Who to build for

One main user and one potential buyer (can differ). User might be a developer, service worker, teacher, AI procurement team, small business, or someone affected by an AI decision. Design around one workflow. Identify who benefits, who could be harmed, who can put mistakes right.

Any sector. Themes: fairness, privacy, security, reliability, transparency, accessibility, human oversight, participation, environmental impact. Pick the risks that matter for your user and make the improvement testable.

**Does not fit:**

- a generic chatbot, ethics checklist or dashboard with no specific user, decision or action;
- claims that a system is "fair", "safe" or "compliant" without defined scope and evidence;
- an earlier project resubmitted, or a demo depending on restricted systems or real sensitive personal data.

One track per team. Here, responsible AI must be central to both problem and product.

## What every project must show

- **A real problem and people affected.** Who, how often, what they do today. Research, published evidence or a conversation with someone affected. A concrete benefit or harm, not a general AI concern.
- **AI at the core.** The AI capability the product uses or improves. An assurance tool qualifies by testing or governing a running AI system; it does not need an LLM inside the checker. Compare the important step against a baseline (rules, manual review, or the same model without your safeguard).
- **A product that works.** User completes the main task end to end. Public or openly licensed material, reproducible test cases, sources and dates visible. Label synthetic inputs. **Keep test cases separate from tuning examples. Report sample sizes as well as results.**
- **A business case.** User, paying customer or funder, problem cost, price or funding model, route to a first pilot. Estimate AI, hosting and human-review cost per use. Why a buyer picks you over existing tools; what changes for a second customer.
- **Evidence of responsibility and honest limits.** One measurable improvement and its trade-off (e.g. fewer unsupported answers at the cost of more handoffs). Demonstrate one failure and what happens next. State who can review, override or challenge the output, and what evidence is still needed before real deployment.

## Directions they want to see

Optional, research-informed. The products and buyers are proposals to validate, not proven.

1. **Release check for customer-support AI.** Based on RAGAs [2]. Run test questions against a support chatbot, highlight unsupported claims, create a review queue. Buyer: software company or support agency, per bot or per test run. Data: licensed public help pages, answerable and unanswerable questions. Compare against the bot without the check; measure missed errors and false alarms vs human labels.
2. **Fairness check before an AI update.** Based on Gender Shades [3]. Release-review tool for one classifier (e.g. routing customer requests). Buyer: product team, subscription. Labelled synthetic cases or a licensed benchmark; compare versions, show subgroup error rates, sample sizes, trade-offs. Do not infer sensitive traits from names or faces.
3. **Evidence assistant for buying AI.** Based on Model Cards [4] and Datasheets for Datasets [5]. Compare a buyer's needs with supplier documentation, quote supporting passages, flag missing evidence for human review. Buyer: small company, procurement team, consultancy, per assessment. Test on public model cards plus fictional supplier packs with planted omissions. Compare against a manual checklist; measure missed gaps, invented claims, review time. Sell faster evidence review, not certification.
4. **Service tool that knows when to hand over.** Based on SelectiveNet [6] (reject option, error vs coverage). Route maintenance requests automatically when evidence is sufficient, send uncertain ones to a worker. Buyer: facilities provider, per site or request. Synthetic requests incl. ambiguous and unfamiliar ones. Compare with routing everything automatically; report errors, automation rate, human queue. Show what happens when the reviewer is unavailable.

## Data

No compulsory dataset, model or framework. Check reuse rights before building.

| Source | What it offers | Access and limits |
|---|---|---|
| Ragas repository | Evaluation tools for LLM apps, linked to RAGAs [2] | Apache-2.0. Model/API use may cost money; validate scores with human checks |
| Fairlearn | Metrics and methods for performance across groups | MIT. Dataset licences separate; no single metric guarantees fairness |
| Hugging Face model cards | Public docs of intended use, evaluation, limitations | Check each repo's terms. Public access is not reuse rights |
| Public manuals and help pages | Material for grounded answers and evidence review | Choose content with reuse permission; record owner, version, URL, date |
| Labelled synthetic test cases | Fictional records, planted errors, ambiguous inputs, controlled group comparisons | State how cases and labels were made. Keep a held-out test set; no population-level claims |

Keep secrets out of the repo. README records model and tool versions, data licences, test-set construction and the limits of the evidence.

## Track rules

Event-wide rules apply. Plus:

- Build during the event; create the repo after hacking opens. Earlier projects are not allowed.
- Credit research, code, models and data with dates and licences. Disclose AI-generated work, prior components and outside help in the README.
- Label cached and synthetic data. Show uncertainty. No safety, fairness or compliance claims beyond what the tests support.
- No private customer records or sensitive personal data in the demo. Do not send confidential information to external AI services. Test only systems you own or are authorised to test.
- Sandbox only, no real consequential decisions about people. For health, safety, legal or financial uses, show qualified human review and link to official guidance.

## Judging emphasis

Same criteria and weights as every track, but responsible AI shapes the evidence across all five:

| Criterion | Weight | What judges should see |
|---|---|---|
| Problem and user | 20% | Specific need, credible evidence, understanding of affected people |
| AI at the core | 20% | Demonstrated AI capability or assurance function, tested against a sensible baseline |
| Working product | 25% | End-to-end task, reproducible tests, a demonstrated failure or handoff |
| Business and scale | 20% | Buyer, value proposition, realistic costs, differentiation, second-customer plan |
| Responsibility and trust | 15% | Measured risk reduction, honest trade-offs, provenance, meaningful human control |

## Track-specific pitch questions

1. What problem and AI-related risk have you evidenced?
2. Who would adopt and pay, and why?
3. What would it take to serve a second customer responsibly?

Show the working core, one failure, the measured benefit and the cost of your safeguard.

## References

1. RAi UK. Research overview.
2. Es, S., James, J., Espinosa Anke, L. & Schockaert, S. (2024). RAGAs: Automated Evaluation of Retrieval Augmented Generation. EACL System Demonstrations, 150-158.
3. Buolamwini, J. & Gebru, T. (2018). Gender Shades: Intersectional Accuracy Disparities in Commercial Gender Classification. PMLR 81, 77-91.
4. Mitchell, M. et al. (2019). Model Cards for Model Reporting. FAT*. arXiv:1810.03993.
5. Gebru, T. et al. (2021). Datasheets for Datasets. Communications of the ACM. arXiv:1803.09010.
6. Geifman, Y. & El-Yaniv, R. (2019). SelectiveNet: A Deep Neural Network with an Integrated Reject Option. PMLR 97, 2151-2159.
