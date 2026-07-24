# Investor Targeting Platform — Backend & Octen Module Spec

Implementation spec. Written to be fed to Claude Code as the working brief.

**Scope of this document:** backend service, the Octen retrieval module, the OpenAI layer, and the data contract the Composio module consumes. The Composio module's internals are specified only at the interface level — another owner builds it.

---

## 0. Rules for the implementing agent

- Build **incrementally, milestone by milestone** (§11). Do not scaffold the whole system at once.
- **Never invent Octen response field names.** The adapter in `octen/client.py` is the only place that touches Octen's wire format. If the real response shape differs from the assumed shape in §5.2, fix it there and nowhere else.
- Every module boundary is a Pydantic model. No dicts crossing module boundaries.
- All I/O is async. No blocking HTTP calls anywhere in the pipeline.
- Write tests against recorded fixtures, not the live API.

---

## 1. What this system does

Given a company profile, produce a ranked list of ~60–80 investors, each carrying **dated evidence** of why they are a fit, verified fresh at request time. That evidence is then handed to the Composio module, which uses the strongest fact to draft outreach for human approval.

Core principle: **the evidence that qualifies an investor is the same artifact that personalizes the email.** One retrieval pass produces both. Do not build separate research and personalization paths.

Hard rule enforced in code: **an investor with zero evidence records is dropped from the list.** Not scored low — dropped.

---

## 2. Stack

- Python 3.11+, FastAPI, Pydantic v2
- `httpx.AsyncClient` for all outbound HTTP
- `asyncio` for concurrency (no Celery in v1)
- OpenAI Python SDK — structured outputs
- Postgres via SQLAlchemy 2.x async, or SQLite for local dev
- Redis for the retrieval cache (optional in v1; in-memory TTL dict acceptable)

---

## 3. Repo layout

```
app/
  main.py                 FastAPI app, routes
  config.py               env/settings (pydantic-settings)
  models/
    profile.py            CompanyProfile
    plan.py               SearchIntent, SearchPlan
    retrieval.py          OctenQuery, OctenResult, RetrievalBundle
    evidence.py           EvidenceRecord, InvestorRecord
    output.py             TargetList, TargetRow   <- Composio contract
  octen/
    client.py             thin async wrapper over api.octen.ai
    planner.py            profile -> SearchPlan (OpenAI)
    executor.py           SearchPlan -> RetrievalBundle (fan-out)
    extractor.py          RetrievalBundle -> EvidenceRecord[] (OpenAI)
    verifier.py           freshness re-check pass
    scorer.py             ranking + list cap
    cache.py
  pipeline.py             orchestrates the 6 stages
  store/
    repo.py               persistence
tests/
  fixtures/               recorded Octen + OpenAI responses
```

---

## 4. Config

```
OCTEN_API_KEY=
OCTEN_BASE_URL=https://api.octen.ai
OCTEN_MAX_CONCURRENCY=64
OCTEN_TIMEOUT_S=10
OCTEN_CACHE_TTL_S=900

OPENAI_API_KEY=
OPENAI_MODEL_PLANNER=          # pin explicitly in .env
OPENAI_MODEL_EXTRACTOR=        # smaller/cheaper model — this runs hundreds of times
OPENAI_MAX_CONCURRENCY=16

LIST_CAP=80
MIN_EVIDENCE_PER_INVESTOR=1
FRESHNESS_MAX_AGE_DAYS=120     # per-type overrides in verifier.py
```

Verify current OpenAI model identifiers before pinning — do not hardcode a model name in source.

---

## 5. The Octen module

### 5.1 What we know about the API

- `POST https://api.octen.ai/search`
- Auth: `X-Api-Key` header
- Supports domain filtering (include/exclude), text filtering (require/exclude text in results), time-based filtering by publication or crawl date, and full page content extraction with a configurable token limit
- Designed for very high concurrency; sub-100ms P50; index refreshes within minutes of publication

The time filter and the domain filter are the two most important knobs for us — they are how freshness and source quality get enforced at retrieval time rather than in post-processing.

### 5.2 `octen/client.py`

Single responsibility: translate `OctenQuery` → HTTP → `list[OctenResult]`.

```python
class OctenQuery(BaseModel):
    query: str
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    published_after: date | None = None      # freshness enforcement
    require_text: list[str] | None = None    # e.g. firm name, to cut noise
    max_results: int = 10
    extract_content: bool = False            # full-page extraction; expensive
    content_token_limit: int | None = None

class OctenResult(BaseModel):
    url: str
    title: str | None
    snippet: str | None
    content: str | None                      # only when extract_content
    published_at: datetime | None            # may be absent — handle None
    crawled_at: datetime | None
    raw: dict                                # keep the untouched payload
```

Requirements:
- Map our field names to Octen's actual request/response keys **inside this file only**. Keep `raw` so nothing is lost if we mapped a field wrong.
- Retry on 429 and 5xx: exponential backoff, honour `Retry-After` if present, max 3 attempts.
- Timeout per request from config; a timeout is a soft failure — return empty results and record the failure, never raise into the pipeline.
- Emit per-query timing so we can prove the concurrency story in the demo.

### 5.3 `octen/planner.py` — profile to search plan

Input `CompanyProfile`, output `SearchPlan`. This is an OpenAI call with a strict JSON schema.

```python
class SearchIntent(BaseModel):
    kind: Literal[
        "adjacent_portfolio",   # funds backing companies like ours
        "thesis_signal",        # partners publishing on our space
        "fund_activity",        # new fund closes, active deployment
        "geo_crossing",         # funds investing into our region
        "portfolio_gap",        # relevant portfolio, missing our category
        "recent_exit",
    ]
    rationale: str
    queries: list[str]          # 5-30 concrete query strings
    domain_hints: list[str] = []
    recency_days: int | None = None
```

The planner's job is **breadth**. It should emit 150–400 queries total across intents. This is the step that justifies using Octen at all — if the plan produces 10 queries, a conventional search API would do and the product has no reason to exist.

Prompt guidance: instruct the model to generate *narrow, specific* queries (firm names, company names, category phrases), not broad ones. Broad queries return the same generic results 300 times.

### 5.4 `octen/executor.py` — the fan-out

```python
async def execute(plan: SearchPlan) -> RetrievalBundle
```

- Flatten all intents into `OctenQuery` objects.
- Dedupe identical query strings before firing.
- Run under `asyncio.Semaphore(OCTEN_MAX_CONCURRENCY)`, gathering with `return_exceptions=True`.
- Apply `published_after` from `recency_days` on the intent.
- Attach the originating intent to every result so the extractor knows what it was looking for.
- Cache by hash of the full query object, TTL from config. Critical during development — you will re-run the same plan dozens of times.
- Record wall-clock time for the whole fan-out. Surface it in the API response; it is a selling point.

Two-phase retrieval: run everything with `extract_content=False` first. Only re-fetch with content extraction for the top ~50 URLs that survive initial extraction. Full-content extraction on 400 URLs is slow and unnecessary.

### 5.5 `octen/extractor.py` — results to evidence

The most important module in the system. Turns raw results into structured, **dated** facts.

```python
class EvidenceRecord(BaseModel):
    investor_firm: str
    investor_person: str | None
    kind: Literal[
        "portfolio_investment", "thesis_publication", "fund_close",
        "portfolio_gap", "exit", "personnel", "other",
    ]
    claim: str                  # one sentence, factual, no adjectives
    event_date: date | None     # date the EVENT happened
    source_url: str
    source_published_at: date | None
    confidence: float           # 0-1
```

Rules to encode in the prompt and enforce in code after the call:
- **A record with no `source_url` is discarded.** No exceptions.
- **A record with neither `event_date` nor `source_published_at` is discarded.** Undated evidence is not evidence.
- `claim` must be checkable against the source text. Instruct the model to refuse to infer.
- Batch results into the extraction call (10–20 results per call) with concurrency capped by `OPENAI_MAX_CONCURRENCY`. Use the smaller model here; this is the volume path.
- Use structured output / JSON schema mode. Never parse free text.

Then normalize firm names (strip `Ventures`/`Capital`/`Partners` suffixes for matching, keep the display name) and group evidence under `InvestorRecord`.

### 5.6 `octen/verifier.py` — the freshness pass

This is the product's actual differentiator. Do not skip it to save time.

For each investor that survives extraction, issue targeted verification queries with a tight `published_after`:

- Is this person still at this firm? (`personnel` check)
- Has the fund made a visible investment recently? (`fund_activity`)
- Has the fund closed a new vehicle?

Then apply per-type staleness thresholds — these decay at very different rates:

| Evidence kind | Max age before re-verification |
|---|---|
| `personnel` | 30 days |
| `fund_close` | 180 days |
| `portfolio_investment` | 90 days |
| `thesis_publication` | 365 days |
| `portfolio_gap` | 90 days |

Attach a `verified_at` timestamp and a `stale: bool` to every record. Stale records may still be shown but must not be used as the email's opening fact.

### 5.7 `octen/scorer.py`

Score on evidence strength × recency × kind weight. Then:

- Drop any investor below `MIN_EVIDENCE_PER_INVESTOR`.
- Truncate to `LIST_CAP`.
- **If fewer than ~30 investors qualify, return a `list_underfilled` warning in the response.** This is a feature: it means the company profile is too vague, and saying so is genuinely useful.
- Founder-context signals (shared school, shared region) apply as a **tiebreaker only** — a small bonus among already-qualified candidates. They must never promote an investor onto the list. Implement as a post-sort nudge, not a scoring term, so this can't drift.

---

## 6. OpenAI usage summary

| Call site | Purpose | Model | Volume |
|---|---|---|---|
| `planner.py` | profile → 150–400 queries | larger | 1 per run |
| `extractor.py` | results → evidence records | smaller | 20–40 per run (batched) |
| `verifier.py` | interpret verification results | smaller | ~n_investors |
| Composio module | draft email from evidence | larger | 1 per investor, on demand |

All calls use structured outputs with an explicit JSON schema. Set `temperature` low (0–0.3) everywhere except drafting. Log token usage per stage — extraction will dominate cost and you will want the number.

---

## 7. Contract with the Composio module

This is the handoff. The backend produces `TargetList`; the Composio module consumes it and owns everything after.

```python
class TargetRow(BaseModel):
    investor_firm: str
    investor_person: str | None
    role: str | None
    score: float
    evidence: list[EvidenceRecord]        # sorted, strongest first
    lead_evidence: EvidenceRecord         # never stale; the email's opening fact
    contact_email: str | None             # may be None — Composio resolves
    firm_domain: str | None
    list_underfilled: bool = False

class TargetList(BaseModel):
    run_id: UUID
    profile_id: UUID
    generated_at: datetime
    rows: list[TargetRow]
    retrieval_stats: RetrievalStats       # query count, wall time, cache hits
    warnings: list[str]
```

### What the Composio module does with it

1. **Prior-contact check** — Gmail lookup on `firm_domain` and `investor_person`. Any prior thread demotes this from cold outreach and is surfaced to the founder instead.
2. **Draft** — 80–120 words, opening from `lead_evidence.claim`. The draft must cite a fact the founder can defend; if `lead_evidence` is stale, the row is drafted as "needs manual review" instead.
3. **Approval queue** — every draft. Nothing sends autonomously. This is a product rule, not a setting.
4. **Send** — from the founder's own domain, via their connected account. Never a shared sending domain.
5. **Log** — write the row plus send status to Sheets or Notion.
6. **Sequence** — follow-ups at ~day 4 and ~day 10, cancelled on reply.

### Guarantees the backend makes to Composio

- `lead_evidence` is present, non-stale, and has a `source_url`.
- Every `EvidenceRecord` is dated and attributable.
- `rows` is sorted by score descending and length ≤ `LIST_CAP`.
- Empty `evidence` never appears. If we can't prove it, we don't ship the row.

The Composio module must **not** do its own research to fill gaps. If the evidence is thin, that is signal to the founder, not a prompt to improvise.

---

## 8. HTTP API

```
POST /profiles                 -> CompanyProfile (create)
POST /runs                     -> {run_id}          starts pipeline, async
GET  /runs/{run_id}            -> status + RetrievalStats
GET  /runs/{run_id}/targets    -> TargetList
GET  /runs/{run_id}/plan       -> SearchPlan        (debug/demo)
POST /runs/{run_id}/reverify   -> re-run verifier only
```

`/runs/{run_id}/plan` exists for the demo — showing the query fan-out is how you make the concurrency visible to a viewer.

---

## 9. Failure handling

- A failed query is a dropped data point, never a failed run. Count failures, expose in `RetrievalStats`.
- If >30% of queries fail, mark the run degraded and say so in `warnings`.
- OpenAI schema violations: one retry, then drop the batch and log. Do not let a malformed extraction poison the list.
- All external calls behind timeouts. The pipeline must always terminate.

---

## 10. Observability

Structured logs per stage: query count, wall time, cache hit rate, evidence yield (records per result — expect low, ~0.1–0.3, and that's fine), drop reasons by category, token usage.

Evidence yield is the metric that tells you whether the planner is generating good queries. Track it from day one.

---

## 11. Milestones

**M1 — Octen client.** `client.py` + fixtures. Hardcode one query, print results. Confirm real field names here and fix the mapping.

**M2 — Plan and fan-out.** `planner.py` + `executor.py`. Given a profile, fire 200 queries concurrently and return raw results with timing. No LLM extraction yet.

**M3 — Evidence.** `extractor.py` with strict discard rules. This is the product. Spend the most time here.

**M4 — Verify and score.** `verifier.py` + `scorer.py`. Produce a real `TargetList`.

**M5 — API.** FastAPI routes, persistence, the debug plan endpoint.

**M6 — Handoff.** Freeze the `TargetList` schema, publish it, write a fixture file the Composio module can develop against without running the pipeline.

Do M6's fixture early if the Composio work is happening in parallel — it unblocks the other owner immediately.

---

## 12. Non-goals for v1

Recruiter/job-seeker use case. Warm-intro graph mapping. CRM and pipeline management. Deck scoring. Autonomous sending — permanently, not just v1.

---

## 13. To verify before building

- Octen API access status and rate limits on our account.
- Exact request/response field names — §5.2 is an informed assumption, not documentation.
- Whether Octen's SDK is preferable to raw `httpx` (an SDK is offered; if it handles concurrency and retries well, use it and keep `client.py` as a thin wrapper anyway).
- Current OpenAI model identifiers for the two pinned roles.
