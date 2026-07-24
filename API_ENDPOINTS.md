# API Endpoints — Frontend Reference

Contract between the frontend and the backend. Base path `/api/v1`.

Companion to `BACKEND_SPEC.md` — model names here (`TargetRow`, `EvidenceRecord`, `SearchPlan`) refer to the Pydantic models defined there.

---

## Conventions

- **Auth:** `Authorization: Bearer <token>` on everything except `/auth/*` and `/health`.
- **IDs:** UUIDs.
- **Timestamps:** ISO 8601, UTC, always with timezone.
- **Errors:** consistent envelope, never a bare string.
  ```json
  { "error": { "code": "run_not_found", "message": "...", "details": {} } }
  ```
- **Pagination:** `?limit=50&cursor=<opaque>`; responses carry `next_cursor` (null when exhausted).
- **Idempotency:** `Idempotency-Key` header required on all send operations. Non-negotiable — a double-send to an investor is unrecoverable.
- **Long operations** return `202` with a resource to poll or stream. Never block a request on the pipeline.

---

## 1. Auth & account

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/login` | Email + password or magic link → session token |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/me` | Current user, org, plan, feature flags |
| `PATCH` | `/me` | Update display name, sending name, signature block |

`GET /me` should return `sending_domain_verified: bool` — the frontend must block all send actions until it's true.

---

## 2. Integrations (Composio)

The frontend needs to drive the connection flow and then reflect status.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/integrations` | List available + connected integrations with status |
| `POST` | `/integrations/{provider}/connect` | Start OAuth → returns `{ redirect_url, connection_id }` |
| `GET` | `/integrations/{provider}/status` | Poll during/after OAuth callback |
| `DELETE` | `/integrations/{provider}` | Disconnect |

Providers: `gmail`, `google_sheets`, `notion`.

```json
// GET /integrations
{
  "integrations": [
    { "provider": "gmail", "status": "connected", "account": "hub@…",
      "scopes_ok": true, "connected_at": "2026-07-20T04:11:00Z" },
    { "provider": "notion", "status": "disconnected" }
  ]
}
```

`status` values: `disconnected | pending | connected | error`. When `error`, include `error_reason` so the UI can say "reconnect" rather than "something went wrong."

---

## 3. Company profile

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/profiles` | Create |
| `GET` | `/profiles` | List (a user may run several companies) |
| `GET` | `/profiles/{id}` | Fetch |
| `PATCH` | `/profiles/{id}` | Update |
| `DELETE` | `/profiles/{id}` | Delete |
| `POST` | `/profiles/{id}/validate` | Pre-flight check before spending a run |

`/validate` is worth building. It returns a cheap assessment of whether the profile is specific enough to produce a full list — vague positioning is the main cause of an underfilled list, and catching it before a 400-query run saves the user time and us money.

```json
// POST /profiles/{id}/validate
{ "ok": false,
  "warnings": ["sector_too_broad", "no_stage_specified"],
  "suggestions": ["Name the specific product category, not just 'medtech'"] }
```

---

## 4. Runs

The core object. A run = one full pipeline execution against one profile.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/runs` | Start a run → `202` + `{ run_id, status: "queued" }` |
| `GET` | `/runs` | List runs for the user, newest first |
| `GET` | `/runs/{id}` | Status, stage, progress, stats, warnings |
| `GET` | `/runs/{id}/events` | **SSE stream** of live progress |
| `POST` | `/runs/{id}/cancel` | Cancel in-flight |
| `POST` | `/runs/{id}/reverify` | Re-run freshness pass only, keep evidence |
| `DELETE` | `/runs/{id}` | Delete run + results |

```json
// GET /runs/{id}
{
  "run_id": "…", "profile_id": "…", "status": "running",
  "stage": "extracting",
  "progress": { "queries_total": 312, "queries_done": 312,
                "results": 2841, "evidence": 194, "investors": 0 },
  "retrieval_stats": { "wall_time_ms": 4120, "cache_hits": 0,
                       "failed_queries": 7, "p50_latency_ms": 68 },
  "warnings": [], "started_at": "…", "completed_at": null
}
```

`stage`: `queued | planning | retrieving | extracting | verifying | scoring | complete | failed | cancelled`.

**`GET /runs/{id}/events` matters more than it looks.** The fan-out is the thing that makes this product visibly different, and a progress bar that jumps from 0 to 312 in four seconds is the demo. Stream `stage_changed`, `query_batch_done`, `investor_found`, `run_complete`. Fall back to polling `GET /runs/{id}` every 2s if SSE fails.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runs/{id}/plan` | The generated `SearchPlan` — intents and query strings |

Debug and demo surface. Showing the actual 300 queries is more persuasive than describing them.

---

## 5. Targets

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runs/{id}/targets` | The ranked list, paginated |
| `GET` | `/targets/{target_id}` | One row, full evidence |
| `PATCH` | `/targets/{target_id}` | Set `status`, `notes`, or override `contact_email` |
| `POST` | `/targets/{target_id}/dismiss` | Remove from the working list |
| `GET` | `/runs/{id}/targets/export` | CSV export |

Query params on the list endpoint: `?status=&min_score=&has_email=&stale=&sort=score|firm|recency`.

```json
// GET /runs/{id}/targets
{
  "rows": [
    { "target_id": "…", "investor_firm": "…", "investor_person": "…",
      "role": "Partner", "score": 0.87, "status": "new",
      "contact_email": "…", "firm_domain": "…",
      "evidence_count": 4, "has_stale_evidence": false,
      "lead_evidence": {
        "kind": "portfolio_investment",
        "claim": "…", "event_date": "2026-03-14",
        "source_url": "…", "confidence": 0.91, "stale": false
      }
    }
  ],
  "next_cursor": "…",
  "list_underfilled": false,
  "total": 63
}
```

The list endpoint returns `lead_evidence` inline but not the full evidence array — that comes from `GET /targets/{id}` when a row expands. Keeps the list payload small.

`status`: `new | drafted | approved | sent | replied | dismissed | needs_review`.

Surface `list_underfilled` prominently in the UI. It is a finding about the user's positioning, not an error.

---

## 6. Drafts & approval queue

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/targets/{id}/draft` | Generate a draft from `lead_evidence` |
| `POST` | `/runs/{id}/drafts/bulk` | Generate for N targets → `202`, poll |
| `GET` | `/drafts/{draft_id}` | Fetch |
| `PATCH` | `/drafts/{draft_id}` | Edit subject/body — human edits always win |
| `POST` | `/drafts/{draft_id}/regenerate` | New version, optional `tone` / `angle` hint |
| `GET` | `/drafts/{draft_id}/versions` | Version history |
| `GET` | `/queue` | The approval queue across all runs |

```json
// GET /drafts/{draft_id}
{
  "draft_id": "…", "target_id": "…",
  "subject": "…", "body": "…", "word_count": 104,
  "lead_evidence_id": "…",
  "prior_contact": { "found": true, "last_thread_at": "2025-11-02",
                     "summary": "…" },
  "blockers": [],
  "version": 2, "updated_at": "…"
}
```

`blockers` is the important field. Non-empty means the UI must disable send and explain why. Values: `stale_lead_evidence`, `no_contact_email`, `prior_contact_exists`, `domain_unverified`.

`prior_contact.found: true` should not silently proceed to cold outreach — surface it and let the founder decide whether this is a follow-up instead.

---

## 7. Sending & sequences

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/drafts/{id}/approve` | Mark approved; does not send |
| `POST` | `/drafts/{id}/send` | Send now. Requires `Idempotency-Key` |
| `POST` | `/drafts/{id}/schedule` | Send at a given time |
| `POST` | `/sends/bulk` | Send an approved set. Requires idempotency key |
| `GET` | `/sends/{send_id}` | Delivery status |
| `GET` | `/sequences/{target_id}` | Follow-up schedule and state |
| `POST` | `/sequences/{target_id}/cancel` | Stop follow-ups |
| `PATCH` | `/sequences/{target_id}` | Adjust follow-up timing |

Two hard rules the API enforces, so the frontend can't bypass them:

- `POST /sends/bulk` rejects any draft not individually approved. Bulk approval is not offered as an endpoint, deliberately — approval is per-message, and building a "approve all" affordance would defeat the product's central premise.
- All sends are rejected with `409` when `sending_domain_verified` is false.

Sequence object:
```json
{ "target_id": "…", "state": "active",
  "steps": [
    { "n": 1, "sent_at": "2026-07-23T09:00:00Z", "status": "delivered" },
    { "n": 2, "scheduled_for": "2026-07-27T09:00:00Z", "status": "pending" },
    { "n": 3, "scheduled_for": "2026-08-02T09:00:00Z", "status": "pending" }
  ],
  "stop_reason": null }
```

`state`: `active | stopped_reply | stopped_manual | complete`. Replies cancel remaining steps automatically; the frontend should show that as a positive event, not a cancellation.

---

## 8. Replies & pipeline view

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/replies` | Detected replies across all sends |
| `GET` | `/pipeline` | Counts by status for the dashboard |

```json
// GET /pipeline
{ "sent": 41, "opened": null, "replied": 9, "meetings": 3,
  "by_run": [ { "run_id": "…", "sent": 41, "reply_rate": 0.22 } ] }
```

Reply rate per run is the number that tells you whether the tool works. Put it on the dashboard from day one.

---

## 9. Logging destinations

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/export/destinations` | Configured Sheets/Notion targets |
| `POST` | `/export/destinations` | Add one |
| `POST` | `/runs/{id}/export` | Push a run's targets to a destination |

---

## 10. System

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/usage` | Runs used, queries consumed, token spend this period |

`/usage` matters earlier than you'd expect — extraction dominates cost and you'll want it visible while tuning.

---

## Build priority for the frontend

If you're cutting scope, this is the order that gets you a working demo:

1. `POST /runs` → `GET /runs/{id}/events` → `GET /runs/{id}/targets`
2. `GET /targets/{id}` (evidence expansion)
3. `POST /targets/{id}/draft` → `PATCH /drafts/{id}` → `POST /drafts/{id}/send`
4. Everything else

Steps 1–3 are the entire product. The single screen showing a ranked list, each row expanding into dated evidence and a draft, is what you demo.
