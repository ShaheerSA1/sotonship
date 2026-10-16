# Judging and how to win

Source: `source-pdfs/judging-and-how-to-win.pdf`, captured from https://live.sotonship.space/judging on 16 Oct 2026, 21:17. Track lenses pasted from the same page.

## The Ship test

The winner is the project a real customer would start using next month and that could still be growing in a year. Every team gets asked:

1. **Would someone actually use this?** A named user with a painful problem, not "everyone".
2. **Is AI the reason it works?** Remove the AI and the product should stop doing its core job.
3. **Does it really work?** A live, end-to-end demo on real data, including what happens when it fails.
4. **Could it become a business?** Someone pays, or benefits enough to fund it, and it grows beyond the first customer.
5. **Can people trust it?** Data it has the right to use, privacy protected, honest about its limits.

Not rewarded: slides without a product, feature count, how advanced the model is.

## The five criteria

Same for every track. Each scored 1 to 10, then weighted.

| # | Criterion | Weight | Judges ask |
|---|---|---|---|
| C1 | Problem and user | 20% | Who exactly has this problem? How painful, how frequent? What evidence (data, a regulation, a real user conversation)? What do they do today? |
| C2 | AI at the core | 20% | Could this be done without AI? Is AI the right tool or would a rule, form or spreadsheet do? Sensible model choice, grounded outputs, comparison against a simple baseline? |
| C3 | Working product | 25% | Does the core task run end to end, live? Real data, not mock-ups? What happens with bad input or missing data? Evidence it works (test cases, accuracy vs baseline, known failures)? |
| C4 | Business and scale | 20% | Who pays and why? Cost per user including AI inference? First three customers? What stops a big player copying it? What changes at 10x or 100x? Works beyond its first market? |
| C5 | Responsibility and trust | 15% | Right to use the data? Personal data minimised and protected? What harm when it is wrong, and who catches it? Limits and uncertainty shown to the user? Legal or regulatory blockers? |

```
Weighted score = 0.20×C1 + 0.20×C2 + 0.25×C3 + 0.20×C4 + 0.15×C5
```

| Score | Meaning |
|---|---|
| 1-2 | Missing or not shown |
| 3-4 | Claimed, but weak evidence |
| 5-6 | Solid for a hackathon |
| 7-8 | Convincing, with few gaps |
| 9-10 | Would hold up in front of a real customer or investor |

## Track lenses

Each track adds extra questions under the same criteria. Answer them in the pitch.

### Southampton City (Council)

| Criterion | Extra questions |
|---|---|
| Problem and user | What is the impact on Southampton, and on whom (residents, council officers, businesses, visitors)? What local evidence shows the problem exists here? |
| AI at the core | What does AI do that a council webpage or form cannot? |
| Working product | Does it run on genuine Southampton data, dated and sourced? What happens outside the area it covers? |
| Business and scale | Who would own and fund it: the council, a service provider, residents, local businesses? Niche to Southampton, or could it work in other UK cities and councils? What would it need to move to a second city? What outcome would a council measure (time saved, reports resolved, emissions cut)? |
| Responsibility and trust | Does it work for people who are less digital, older or have access needs? Does it avoid sending non-public council information to external AI services? If it gives safety information, does it point to official sources? |

### FinTech

| Criterion | Extra questions |
|---|---|
| Problem and user | Which user in a bank, fintech, business or household has this problem? What does it cost them today in money, time or risk? |
| AI at the core | Why does this need AI rather than fixed rules? How does it cope when fraudsters or markets adapt? |
| Working product | How often is it wrong, and what does each error cost (false alarms vs missed cases)? Was it tested against a simple baseline? |
| Business and scale | Who pays: a bank, a merchant, a consumer? How would it plug into existing systems (APIs, payment standards)? Could one of our partner banks (Deutsche Bank, JPMorganChase, TrueMoney) realistically adopt it? |
| Responsibility and trust | Can it explain a decision to a customer or a regulator? Which rules apply (e.g. FCA Consumer Duty, anti-money-laundering, data protection)? Is customer data handled lawfully? |

### Responsible AI

| Criterion | Extra questions |
|---|---|
| Problem and user | A specific need, credible evidence and an understanding of affected people. |
| AI at the core | A demonstrated AI capability or assurance function, tested against a sensible baseline. |
| Working product | An end-to-end task, reproducible tests and a demonstrated failure or handoff. |
| Business and scale | A buyer, value proposition, realistic costs, differentiation and a second-customer plan. |
| Responsibility and trust | Measured risk reduction, honest trade-offs, provenance and meaningful human control. |

## What to submit

Everything goes on the team page on SotonShip Live. **Locks Sun 18 Oct, 13:00.** Extensions only in special circumstances. An incomplete submission is not shown in Stage 1.

- **Pitch video (YouTube link):** public or unlisted, 1:00 to 3:00. Must show the real product working (screen recording of the live product). Mock-ups or slides alone do not count.
- **Pitch format:** either a video that fills the whole slot, or a shorter video plus a live talking pitch for the rest. Tell them which, and the video length.
- **Project summary:** up to 150 words. User and problem, why it matters, the solution, how it scales.
- **GitHub repository:** public. README covers setup, data sources (with dates and licences), what the AI does, what was AI-generated or pre-existing, test results and known limits.
- **Live link or run instructions:** optional, encouraged.

## Suggested 3-minute pitch

| Time | Content |
|---|---|
| 0:00-0:20 | The user and their problem, with one piece of evidence |
| 0:20-1:40 | Demo of the core task, start to finish (must be in the video) |
| 1:40-2:10 | Why AI: what it does, and proof it beats a simple approach |
| 2:10-2:45 | The business: who pays, what it costs, how it grows |
| 2:45-3:00 | Limits and trust, then what you would build next |

## How to win (organiser advice)

- Pick one user and one task. Depth beats breadth.
- The impact of the idea matters.
- Talk to a real potential user during the weekend (mentors, partners, other participants) and quote them.
- Core task working end to end by **Saturday evening**, then polish.
- Measure it: a few test cases, a baseline, the failures you found.
- Put a number on the business: what someone pays and what it costs to run.
- Record the video before the deadline. Do not spend the last hour on features nobody will see.
- Show a failure honestly.

## Stage 1: VC for a Day

Sunday afternoon. Every team pitches, track by track, random order.

**Each slot:** up to 3:00 of pitch (video plus any live pitch), then 1:00 Q&A. Anyone can post and upvote questions on the team page while it pitches. Moderator reads the top ones, judges' first.

**Investment rules:**

- £10,000 per person per track, only spendable in that track. Unspent money is lost.
- Cannot invest in your own team.
- Must back at least 3 teams, max £4,000 in any one team.
- Allocation can change while the track is open. Last save counts. Closes a few minutes after the last pitch.
- Judges invest only in their assigned track, same rules, counted separately.

**Scoring (within a track):**

```
public_share = public £ in the team / all public £ in the track
judge_share  = judge £ in the team  / all judge £ in the track
stage1_score = 0.7 × public_share + 0.3 × judge_share
```

Ties go to higher judge share, then higher average judge score. Results hidden until all three tracks finish. **Top 3 per track go to Stage 2.**

**People's Choice:** symbolic prize for the team that raised the most public money across the whole event.

## Stage 2: the panel

- Judges score only finalists in their assigned track.
- About 10 minutes per team: **2:00 live demo where the panel gives it one input of its own choosing**, then 5:00 panel Q&A.
- Stage 1 ranking carries no weight. Every finalist starts level.
- Panel decides 1st, 2nd, 3rd per track, then picks the overall winner from the three track winners.
