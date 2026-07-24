# Octen Pipeline Output — Contract for the Composio Module

**Audience:** whoever is building the `composio/` package.
**Purpose:** describes exactly what the retrieval/scoring pipeline hands you, field by field, with a worked example. This is the input to your module — everything upstream of it (planning, Octen search, extraction, verification, scoring) is out of scope for you and already built.
**Source of truth:** `backend/app/models.py` (`TargetList` / `TargetRow` / `EvidenceRecord`, labeled in that file as "Stage 6: output (the Composio contract)"). If this doc and the code ever disagree, the code wins — ping the pipeline owner to reconcile.

---

## 1. Where the handoff happens

The pipeline (`backend/app/pipeline.py`) runs six stages — plan → retrieve (Octen) → extract → verify (Octen) → score → save. The final stage produces a `TargetList` and saves it via `RunStore`. That's the boundary: your module consumes a `TargetList`, nothing upstream of it.

**Currently implemented endpoint:**

```
GET /runs/{run_id}/targets  →  TargetList (full, unpaginated)
```

Note: `API_ENDPOINTS.md` §5 describes this as a *paginated* endpoint returning `TargetsPage` (list of lightweight `TargetSummary` rows + a separate `GET /targets/{id}` for full evidence). That pagination layer **does not exist yet** in `main.py` — today the endpoint returns the entire `TargetList` with full `TargetRow`s, evidence arrays included. Build against the paginated shape if you're matching the spec doc, but know the live endpoint right now returns the fuller shape below.

---

## 2. The shape: `TargetList`

```python
class TargetList(BaseModel):
    run_id: UUID
    profile_id: UUID
    generated_at: datetime
    rows: list[TargetRow]
    retrieval_stats: RetrievalStats
    warnings: list[str] = []
```

`rows` is the ranked, capped investor list — this is your input queue for drafting and sending. `warnings` and `retrieval_stats` are informational (surfaced in the UI, not something your module acts on), described briefly in §5.

---

## 3. Each row: `TargetRow`

```python
class TargetRow(BaseModel):
    target_id: UUID
    investor_firm: str
    investor_person: str | None = None
    role: str | None = None
    score: float
    evidence: list[EvidenceRecord]       # sorted, strongest first
    lead_evidence: EvidenceRecord        # never stale — the email's opening fact
    contact_email: str | None = None     # ALWAYS None coming out of scoring
    firm_domain: str | None = None       # ALWAYS None coming out of scoring
    list_underfilled: bool = False
    status: Literal["new", "drafted", "approved", "sent", "replied", "dismissed", "needs_review"] = "new"
    notes: str | None = None
```

### The one thing you need to know before anything else

`contact_email` and `firm_domain` are **hardcoded to `None`** when a row is built (`scorer.py:86-87`, comment: `# resolved by the Composio module`). Octen retrieval and the scoring stage never attempt contact resolution — that's explicitly assigned to your module. Every row you receive needs an email/domain lookup before a draft can be sent. This is why `blockers` includes `no_contact_email` in the drafts contract (`API_ENDPOINTS.md` §6) — expect most fresh rows to start there.

### `lead_evidence` guarantee

`lead_evidence` is guaranteed non-stale — the scorer drops any investor whose evidence is *all* stale, and picks the strongest fresh record as `lead_evidence` (`scorer.py:71-76`). This is the fact your draft should open with. The design doc for your module (`2026-07-23-composio-integration-design.md` §4.3) still says to treat `lead_evidence.stale` as defense-in-depth rather than trusting this blindly — do that, but know it should never actually fire.

### `evidence` vs `lead_evidence`

`evidence` is the *full* list for that investor (all evidence, stale included), sorted strongest-first by `confidence × kind_weight × recency_decay`. `lead_evidence` is one specific (non-stale) item pulled from that list — the single fact to lead the email with, not a summary.

### `status`

Starts at `"new"` for every row out of scoring. Your module (via `PATCH /targets/{id}` and the draft/send endpoints) is what moves it through `drafted → approved → sent → replied`, or `dismissed`/`needs_review`. The pipeline itself never writes anything but `"new"`.

### `score`

Sum of each evidence record's `confidence × kind_weight × recency_decay` (see `scorer.py` for weights). Useful for sorting/prioritizing your send queue; not something to re-derive or display as a probability.

---

## 4. Each evidence record: `EvidenceRecord`

```python
class EvidenceRecord(BaseModel):
    investor_firm: str
    investor_person: str | None = None
    kind: Literal["portfolio_investment", "thesis_publication", "fund_close",
                   "portfolio_gap", "exit", "personnel", "other"]
    claim: str                          # the actual fact, in prose
    event_date: date | None = None
    source_url: str
    source_published_at: date | None = None
    confidence: float                   # 0.0–1.0
    verified_at: datetime | None = None # set by the verify stage
    stale: bool = False
```

`claim` is what you pass to OpenAI for draft generation — it's already a checkable, dated fact (e.g. "Acme Ventures led a $4M seed round in a competing analytics tool in March 2026"), not a raw snippet. `source_url` is there for the draft to optionally cite. `stale` means the verify stage re-checked this fact and it no longer holds (e.g. the source URL 404s or the underlying event has been superseded) — never use a stale record as `lead_evidence` yourself if you're picking a different one than the one supplied.

---

## 5. Informational fields (read-only for your module)

```python
class RetrievalStats(BaseModel):
    query_count: int
    result_count: int
    failed_query_count: int
    wall_time_s: float
    cache_hit_count: int = 0
    p50_latency_ms: float | None = None
```

`warnings` on `TargetList` is a `list[str]`, currently populated with at most two strings:
- `"run degraded: over 30% of retrieval queries failed"` — Octen had a bad run; evidence coverage may be thin.
- `"list_underfilled: fewer than 30 investors qualified -- profile may be too vague"` — also mirrored per-row as `TargetRow.list_underfilled`.

Neither should block your module from drafting/sending — they're UI signals, not error states.

---

## 6. Worked example

```json
{
  "run_id": "6f9a2b3e-1c4d-4e8a-9b7f-2d3c4e5f6a7b",
  "profile_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  "generated_at": "2026-07-23T14:32:07Z",
  "rows": [
    {
      "target_id": "9c8b7a6d-5e4f-4a3b-2c1d-0e9f8a7b6c5d",
      "investor_firm": "Acme Ventures",
      "investor_person": "Jane Rivera",
      "role": "Partner",
      "score": 1.42,
      "evidence": [
        {
          "investor_firm": "Acme Ventures",
          "investor_person": "Jane Rivera",
          "kind": "portfolio_investment",
          "claim": "Acme Ventures led a $4M seed round in Rowlift, a competing analytics tool, in March 2026.",
          "event_date": "2026-03-14",
          "source_url": "https://techcrunch.com/2026/03/14/rowlift-seed/",
          "source_published_at": "2026-03-14",
          "confidence": 0.91,
          "verified_at": "2026-07-20T09:00:00Z",
          "stale": false
        },
        {
          "investor_firm": "Acme Ventures",
          "investor_person": "Jane Rivera",
          "kind": "thesis_publication",
          "claim": "Jane Rivera published a thesis piece on 'the future of vertical SaaS analytics' in Jan 2025.",
          "event_date": "2025-01-10",
          "source_url": "https://acmeventures.com/blog/vertical-saas-analytics",
          "source_published_at": "2025-01-10",
          "confidence": 0.75,
          "verified_at": "2026-07-20T09:00:01Z",
          "stale": true
        }
      ],
      "lead_evidence": {
        "investor_firm": "Acme Ventures",
        "investor_person": "Jane Rivera",
        "kind": "portfolio_investment",
        "claim": "Acme Ventures led a $4M seed round in Rowlift, a competing analytics tool, in March 2026.",
        "event_date": "2026-03-14",
        "source_url": "https://techcrunch.com/2026/03/14/rowlift-seed/",
        "source_published_at": "2026-03-14",
        "confidence": 0.91,
        "verified_at": "2026-07-20T09:00:00Z",
        "stale": false
      },
      "contact_email": null,
      "firm_domain": null,
      "list_underfilled": false,
      "status": "new",
      "notes": null
    }
  ],
  "retrieval_stats": {
    "query_count": 312,
    "result_count": 891,
    "failed_query_count": 4,
    "wall_time_s": 18.42,
    "cache_hit_count": 22,
    "p50_latency_ms": 640.5
  },
  "warnings": []
}
```

---

## 7. Practical checklist for your module

- [ ] Treat `contact_email` / `firm_domain` as **always absent** on ingest — resolving them is your first job per row, before a draft is possible.
- [ ] Use `lead_evidence.claim` (not the raw `evidence` array) as the primary input to draft generation — it's already the single strongest, non-stale, checkable fact.
- [ ] Never send if `evidence` (or specifically `lead_evidence`) comes back `stale: true` for a row you're about to act on — re-check at send time, not just at draft time, since time passes between draft and approval.
- [ ] `status` on `TargetRow` is yours to drive forward (`new → drafted → approved → sent → replied/dismissed/needs_review`) via your own endpoints — the pipeline never advances it past `"new"`.
- [ ] `target_id` is stable across pipeline **reverify** runs (matched by firm+person) — safe to use as your foreign key for drafts/sends/sequences.
- [ ] `list_underfilled: true` is not an error — don't suppress sending, just know the list may be thin on quality below the cutoff.
