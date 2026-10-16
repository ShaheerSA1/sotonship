# Track brief: Southampton City

Source: `source-pdfs/southampton-city-brief.pdf`. In collaboration with Southampton City Council.

## The challenge

Build an AI-powered product that solves a real problem for someone who lives, works or visits in Southampton, and that you could put in front of that person after the weekend. Port city of about 250,000 people, shaped by docks, coastline and two rivers. The council runs hundreds of services on a tight budget. Residents, businesses and visitors deal with traffic, air quality, flood risk, housing and access to services. No fixed project list; show it matters here.

A simple tool one council team or one group of residents would use next month beats an impressive prototype nobody adopts.

**One-sentence test:**

> We help [a specific person] to [do or decide something] in [part of Southampton] using [AI and the data behind it].

Example: *We help council street-scene officers clear fly-tipping faster across the city by classifying, merging and routing residents' photo reports.*

## Who to build for

One main user:

- **Resident:** student, family, older person, someone with access needs, tenant, small landlord.
- **Council officer:** planning, highways, street scene, environmental health, housing, customer services.
- **Local business or worker:** retail, hospitality, the port, logistics.
- **Visitor:** cruise passenger, new student.

One neighbourhood, one service or one kind of journey is enough, and usually stronger.

**Fits:** port and coast, transport, environment and climate, housing and planning, streets and public spaces, access to council services.

**Does not fit:**

- a general chatbot about Southampton, or a map or prediction that does not lead to a decision;
- an existing product with an AI feature bolted on;
- anything needing restricted council systems, real personal data, port facility access or physical hardware (unless agreed in advance).

One track per team.

## What every project must show

- **A real local problem.** Who, how often, what they do today, backed by local evidence (data, a council document, a conversation with someone affected). Putting "Southampton" on a generic app does not count.
- **AI the product depends on.** Remove the AI test. If it classifies, predicts or extracts, compare against a simple baseline.
- **Works on real data.** Main task completable live, end to end, on **genuine Southampton data** with source and date visible. Synthetic is fine for testing, labelled.
- **A business case.** Who pays (council, service provider, local businesses, residents), rough cost per user incl. AI, what it takes to work in a second city.
- **Honesty about limits.** What it does not know, how old its data is, what happens with missing data, stale sources or a location outside coverage. **Show at least one failure case in the demo.**

## Directions they want to see

Optional. Original ideas judged on the same terms.

1. **Triage for street reports.** Residents report fly-tipping, potholes, broken street lights as photos and text, often several times for the same issue. Classify, merge duplicates, estimate urgency, route to the right team. Customer: the council; every UK council has the same reports. Data: public FixMyStreet reports for Southampton.
2. **Pre-check for planning applications.** Many householder applications are returned invalid for a missing document or detail. Read a draft application and check it against the validation checklist and Local Plan policies before submission. Sold per check to homeowners and small architects, or licensed by the council. Data: public planning register and published policies.
3. **Licensing support for HMO landlords.** Southampton licenses houses in multiple occupation (large student population). Read a landlord's property details and documents, check against published licence conditions, list what is missing before inspection. Buyers: letting agents, small landlords; reduces failed inspections for the council. Many UK councils run similar schemes.
4. **Cruise-day planning for local businesses.** Cafés, shops and taxi firms staff cruise days by guesswork. Forecast demand from cruise schedule, weather and local events, turn it into staffing and stock advice. Subscription for businesses or the city-centre BID; later other cruise ports. Baseline: same demand as the last comparable cruise day.

## Data

No compulsory dataset. Check early that sources cover Southampton and you may use them.

| Source | What it offers | Access and limits |
|---|---|---|
| Environment Agency flood monitoring | Flood warnings, warning areas, river and tide gauge readings | Open API, no registration; check coverage and timestamps |
| UKHO Admiralty Tidal API | Predicted high and low tides | Free registration and key; check tier, forecast horizon, quota |
| Bus Open Data Service | Bus timetables, vehicle locations, fares | Free registration and key; check which local operators and fields exist |
| Defra UK-AIR | Air quality from Southampton monitoring sites | Public downloads; check pollutants and provisional vs ratified |
| DfT road traffic statistics | Traffic counts, annual average flows at Southampton count points | Public downloads; historical averages, not live |
| Met Office Weather DataHub | Site forecasts incl. wind | Free account and key; check products and allowances |
| Southampton VTS | Cruise schedules and vessel movements | Public web pages; do not assume an API or redistribution rights |
| Southampton Data Observatory | Council statistics on population, economy, services | Public; check dates and geographic detail |
| Southampton City Council | Planning register, Local Plan, HMO licensing conditions, service info | Public pages and documents; check terms before reusing content |

Keep API keys and passwords out of the repo.

## Track rules

Event-wide rules apply. Plus:

- Build during the event; create the repo after hacking opens. Earlier projects are not allowed.
- README states which parts were AI-generated, what existed before and who helped.
- Show where each number comes from and when it was collected. Never present cached as live or synthetic as real.
- Do not collect personal data you do not need. Do not send non-public council information to an external AI service.
- For safety, health or emergencies, link to official guidance instead of writing your own instructions.

## Track-specific pitch questions

1. What local evidence shows the problem is real in Southampton?
2. Who would own and pay for the product?
3. What would it take to run it in a second city?

README must list every data source with its date and licence.
