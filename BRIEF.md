# Investor Targeting & Outreach Platform — Team Brief

**Status:** Concept / pre-build
**Working name:** TBD
**Owner:** Hub
**Last updated:** 23 July 2026

---

## 1. One-liner

A live, verified investor target list where every name arrives with dated evidence and a ready-to-send first line.

## 2. The problem — stated precisely

Founders raising a round lose weeks to investor research, and the work is mostly wasted. The instinct is to say "it's hard to find investors," but that isn't quite the bottleneck. Lists already exist — Crunchbase, PitchBook, OpenVC, Signal, Capwave and others track tens of thousands of investor profiles between them.

Three things are actually broken:

1. **Decay.** Investor data is a periodic snapshot. Partners leave, funds stop deploying, theses shift. Founders routinely email people who left the firm a year ago, or funds that have no dry powder.
2. **Evidence.** A database tells you a fund is "seed / medtech." It doesn't tell you *why this fund, this month*. So founders either send generic emails or spend 20 minutes per investor doing manual research.
3. **The research and the writing are done twice.** The founder researches an investor to decide whether to contact them, then researches again to personalize the email. These should be one step.

Consequence: founders default to volume. Volume is actively harmful — investors compare notes, and mass outreach signals a lack of discipline to exactly the people you want to impress. The best-performing founders send 50–80 highly targeted emails over 3–4 weeks.

## 3. What we're building

You describe your company and round once. The platform returns a ranked list of the ~60–80 investors most likely to fund *that specific round, right now*, and for each one shows exactly why — a set of timestamped facts. It then drafts a short personalized email built from the strongest fact, queues it for human review, and sends and follows up from your own inbox after approval.

**The core design principle:** *the evidence that qualifies an investor and the personalization in the email are the same artifact.* We do not score, then separately research, then separately write. One retrieval pass produces all three.

## 4. Positioning

| | Incumbents | Us |
|---|---|---|
| Data model | Static index, periodically refreshed | Live query layer, verified at request time |
| Output | A filtered list with scores | A list where every row carries dated proof |
| Personalization | Separate step, manual or templated | Falls out of the qualification evidence |
| Optimizes for | Coverage (bigger list) | Precision (fewer, better sends) |

We will never win on database size and should not try. We win on **freshness and evidence.**

## 5. Core steps — the loop

**Step 1 — Profile to search plan**
Founder describes the company and round once (sector, product, stage, geography, target check size). An LLM converts this into a *structured search plan*: a set of intents, not a single query. Intents include adjacent portfolio companies, thesis keywords, geography-crossing funds, recent relevant exits, and portfolio gaps.

**Step 2 — Parallel retrieval (Octen)**
Each intent expands into dozens of concurrent real-time queries. We are not asking one broad question; we are asking several hundred narrow ones simultaneously and assembling the result. This is the step that requires a high-concurrency, low-latency search layer rather than a conventional search API.

**Step 3 — Evidence extraction**
Raw results are distilled into structured, **dated** evidence records attached to an investor or firm. Examples:

- Backed [adjacent company], announced March 2026
- Partner published on emerging-market medical devices, May 2026
- New fund closed January 2026, actively deploying
- Portfolio holds three hearing-adjacent companies, no bone conduction

**Hard rule: no investor enters the list without at least one retrievable, dated piece of evidence.** This single constraint is what stops us from becoming another generic database.

**Step 4 — Freshness verification**
Before any name is surfaced, re-verify the volatile facts: is this partner still at the firm, is the fund still deploying, when was the last visible check. Every fact carries an age; facts past a staleness threshold are re-run rather than served. This is the property incumbents structurally cannot match.

**Step 5 — Scoring and ranking**
Rank on evidence strength and recency. Founder-context signals (shared school, shared major, shared geography) act **only as tiebreakers between already-qualified candidates** — they never promote someone onto the list. Alma mater mentions are weak signal and every investor has seen a thousand of them.

**Step 6 — Draft generation (Composio)**
Check the founder's mail history for any prior contact with the person or firm. Draft 80–120 words, opening from the single highest-scoring evidence fact. Place into an approval queue.

**Step 7 — Human approval**
The founder reads and edits every email. Nothing leaves the system without a click.

**Step 8 — Send and sequence (Composio)**
Send from the founder's own domain. Log to Sheets or Notion. Schedule follow-ups at roughly day 4 and day 10, stopping automatically on reply. Most positive replies arrive on the second or third touch, so the sequencer carries as much weight as the matcher.

## 6. Product rules (non-negotiable)

- **Nothing sends autonomously.** Human approval on every message. This is also our marketing position: we help you send fewer, better emails.
- **Hard list cap (~80).** If we cannot fill the list with evidence, we say so — that is a real signal that the founder's positioning is too vague, and telling them is valuable.
- **Own domain only.** Shared bulk-mail infrastructure gets blocked by institutional spam filters and burns sender reputation.
- **No evidence, no listing.** No exceptions.

## 7. Out of scope for v1

Deliberately excluded, not forgotten:

- Recruiters / job-seeker use case — similar shape, different data, different buyer, different economics. Splitting focus halves the depth of both.
- Warm-intro graph mapping — requires network data we don't have.
- CRM and pipeline management — incumbents do this fine.
- Pitch deck scoring.

## 8. Technical split

- **Octen** — real-time parallel retrieval. Load-bearing because of concurrency and index freshness, not because it is "a search API." If a conventional search API could do the job, the product doesn't work.
- **Composio** — authenticated account actions: mail history lookup, draft creation, domain-authenticated send, sheet/Notion logging, follow-up scheduling.
- **LLM layer** — search planning, evidence extraction into schema, draft writing. Kept narrow: retrieval does the heavy lifting, the model structures and phrases.

## 9. Build order (weekend / hackathon scope)

| Window | Work |
|---|---|
| Hours 0–2 | Composio auth (Gmail + Sheets). End-to-end send-with-approval path working on one hardcoded investor. Do the plumbing while fresh — this is where teams lose the evening. |
| Hours 2–6 | Octen fan-out and the evidence extraction schema. **This is the actual product.** |
| Hours 6–10 | Scoring, dedupe, freshness verification pass. |
| Hours 10+ | The single screen: ranked list, each row expanding into dated evidence plus the draft email. This screen is the demo. |

## 10. Validation — how we'll know it works

We test on our own live raise, not a synthetic dataset.

1. **Did it surface names we had not already found manually?** If not, it's a search box, not a product. This is the question that decides whether this is worth building further.
2. **What fraction of generated evidence lines would we put our name behind?** Target > 70%. Below that, draft quality is the problem, not matching.
3. **Reply rate vs. our manual sends.**

## 11. Open questions

- Octen API access — was invitation-only at launch; confirm availability before committing to the architecture.
- How do we handle firms where the relevant evidence exists but the right partner is ambiguous?
- Staleness threshold per fact type — a fund close and a blog post decay at very different rates.
- Is the buyer a founder mid-raise (acute pain, short LTV — they churn the day they close), or an accelerator/program buying on behalf of a portfolio?
