# Composio Integration — Design

**Status:** Approved, pre-implementation
**Scope:** Full Composio module — the interface `BACKEND_SPEC.md` §7 hands off to another owner: connection lifecycle, prior-contact check, draft generation, approval-gated send, follow-up sequencing, reply detection, and Sheets/Notion logging.
**Relation to other docs:** Implements the Composio side of `API_ENDPOINTS.md` §2 (Integrations), §6 (Drafts & approval), §7 (Sending & sequences), §8 (Replies), §9 (Logging destinations), and the `TargetList` → outreach handoff described in `BACKEND_SPEC.md` §7. Non-negotiable product rules in `AGENTS.md` govern this design and are restated inline where they drive an architecture decision.

---

## 1. Current state

Only `backend/app/composio_client.py` exists: an `lru_cache`d `get_composio()` factory reading `COMPOSIO_API_KEY`, mirroring the pattern in `openai_client.py`. No connection flow, no tool execution, no routes beyond `/api/health`. This design is the next layer on top of that client.

## 2. Core architecture decision: deterministic execution, not agentic tool-calling

Composio can be used two ways: (a) hand its tool schemas to an LLM and let the model decide which actions to call, or (b) call `composio.tools.execute(...)` directly from our own code with arguments we constructed.

**This design uses (b) exclusively for every account action** — prior-contact lookup, send, sheet/Notion logging, trigger registration. OpenAI is used only to generate draft *text*; it never has the ability to call `GMAIL_SEND_EMAIL` or any other Composio tool. This isn't a stylistic preference — `AGENTS.md`'s non-negotiable rule ("nothing sends autonomously... every email requires human approval") and the idempotency guarantee in `API_ENDPOINTS.md` only hold if there is no model in the loop deciding whether an account action fires.

## 3. Module layout

New `composio/` package, mirroring the existing `octen/` module structure from `BACKEND_SPEC.md` §3:

```
app/
  composio_client.py         existing get_composio() singleton — unchanged
  composio/
    integrations.py          connect / status / disconnect  (/integrations endpoints)
    mail.py                  prior-contact lookup (GMAIL_FETCH_EMAILS)
    drafts.py                draft orchestration — OpenAI text + our DB, no Composio send calls
    send.py                  GMAIL_SEND_EMAIL + idempotency enforcement
    export.py                Sheets / Notion logging
    sequences.py             follow-up scheduling + DB-backed sweep
    triggers.py               reply-detection webhook handler + trigger registration
  models/
    integration.py            Integration / ConnectedAccount
    draft.py                  Draft, DraftVersion, Blockers
    outreach.py                Send, Sequence, SequenceStep
```

Every module boundary is a Pydantic model, consistent with `BACKEND_SPEC.md` §0's rule for the Octen module — no dicts crossing into `main.py` routes.

## 4. Components and data flow

**4.1 Connect** (`integrations.py`, → `POST/GET/DELETE /integrations/{provider}`)
`composio.connected_accounts.initiate(user_id=founder.id, auth_config_id=<provider's ac_id>, callback_url=...)` returns a `redirect_url` and a pending connection; we persist `connected_account_id` + status. `GET /integrations` lists via `connected_accounts.list(user_ids=[founder.id])` and maps Composio's `ACTIVE/INITIATED/FAILED` onto the API's `connected/pending/error`. `DELETE /integrations/{provider}` calls `connected_accounts.delete(...)` (confirmed to exist — see §7).

Providers (`API_ENDPOINTS.md` §2): `gmail`, `google_sheets`, `notion`. Each needs its own auth-config ID, created once via the Composio dashboard and passed in as env vars (`COMPOSIO_AUTH_CONFIG_GMAIL`, `_GOOGLE_SHEETS`, `_NOTION`) — not created programmatically per user.

**4.2 Prior-contact check** (`mail.py`)
Deterministic call: `composio.tools.execute("GMAIL_FETCH_EMAILS", user_id=founder.id, connected_account_id=..., arguments={"query": f"to:{contact_email} OR from:{contact_email} OR {firm_domain}"})`. Result feeds `Draft.prior_contact` (`API_ENDPOINTS.md` §6) and the `prior_contact_exists` blocker. A `found: true` result surfaces to the founder rather than silently proceeding, per the spec's explicit instruction.

**4.3 Draft generation** (`drafts.py`, → `POST /targets/{id}/draft`, `/regenerate`)
Pure OpenAI call, no Composio account action. Input: `lead_evidence.claim` + prior-contact summary. Output: 80–120 word draft, versioned on regenerate (`GET /drafts/{id}/versions`). If `lead_evidence.stale` — which `BACKEND_SPEC.md` §7 says should never happen, since the backend guarantees a non-stale `lead_evidence` — the draft is still forced to `status=needs_review` with blocker `stale_lead_evidence` as defense in depth rather than trusting the upstream guarantee blindly.

**4.4 Approve and send** (`send.py`, → `/drafts/{id}/approve`, `/drafts/{id}/send`, `/sends/bulk`)
`Idempotency-Key` is stored under a unique DB constraint keyed to the draft **before** calling Composio. A retried request with the same key returns the cached prior result without a second call to `composio.tools.execute("GMAIL_SEND_EMAIL", ...)` — this holds even if our process crashed mid-request, because the constraint lives in the DB, not in memory. Preconditions checked before send: `sending_domain_verified` true, `blockers` empty, matching the `409`s `API_ENDPOINTS.md` §7 specifies. `POST /sends/bulk` only accepts drafts already individually approved — no bulk-approve endpoint exists, deliberately, per the API doc.

**4.5 Sequencing** (`sequences.py`, → `GET/POST/PATCH /sequences/{target_id}`)
On successful send, insert two `SequenceStep` rows at `scheduled_for` = now+4d and now+10d, `state=active`. `BACKEND_SPEC.md` §2 rules out Celery for v1 in favor of asyncio; consistent with that, follow-ups are driven by a DB-backed sweep task started in the FastAPI lifespan, polling `WHERE status='pending' AND scheduled_for <= now()` roughly every few minutes and reusing the same send path as §4.4 (including idempotency). State lives in the DB rather than an in-memory scheduler, so a restart doesn't lose or double-fire a pending follow-up.

**4.6 Reply detection** (`triggers.py`, → `POST /webhooks/composio`, feeds `GET /replies`)
On connect, register a Gmail new-message trigger per connected account and subscribe one webhook URL for the whole app via `composio.triggers.set_webhook_subscription(webhook_url=...)`. `POST /webhooks/composio` calls `composio.triggers.parse(body=raw_body, headers=headers, verify_secret=COMPOSIO_WEBHOOK_SECRET)` — unverified payloads are rejected outright, not logged-and-ignored. A parsed event is matched to an active `Sequence` by thread/contact; on match, `state` becomes `stopped_reply`, remaining `SequenceStep` rows are cancelled, and the event feeds `GET /replies`. `API_ENDPOINTS.md` §7 wants a reply shown as a positive event, not a cancellation — the frontend consumes `stop_reason: "reply"` to render it that way.

Requires a public URL reachable from Composio's webhook delivery. Local development needs a tunnel (ngrok or similar); this is a setup requirement, not a code path.

**4.7 Export** (`export.py`, → `POST /runs/{id}/export`)
Sheet/Notion append actions per target row, triggered on demand. Exact tool slugs unconfirmed — see §7.

## 5. Error handling

- A failed Composio call becomes a domain-level failure (`Send.status=failed`, a blocker), not a bare 500 — and never triggers an automatic retry of a send, since a retried send is exactly the double-send `API_ENDPOINTS.md` calls "unrecoverable."
- Connected account not `ACTIVE` → `409` with a blocker the frontend already has a rendering path for (same shape as `domain_unverified`).
- Trigger-registration failure at connect time doesn't block the rest of onboarding — it's logged and retryable, since Gmail/Sheets access still works without the reply-detection trigger active.

## 6. Testing

Same discipline `BACKEND_SPEC.md` §0 sets for the Octen client: record real fixtures once (a `connected_accounts.initiate` response, a `tools.execute` send response, a `triggers.parse` webhook payload), then test against those — never the live API. Idempotency and the sequence sweep get unit tests against a mocked Composio client with an injected clock, so a duplicate `Idempotency-Key` or a due `SequenceStep` can be asserted deterministically.

## 7. Open items to verify before implementing

Mirrors `BACKEND_SPEC.md` §13's own caveat about not inventing Octen field names — the same applies here:

- **Gmail reply-trigger slug is ambiguous in current docs** — some sources show `GMAIL_NEW_MESSAGE`, others `GMAIL_NEW_GMAIL_MESSAGE`. Confirm via `composio.triggers.list_types(toolkits=["gmail"])` before hardcoding a slug.
- Exact Sheets/Notion tool slugs for the append/create-page actions — pull from `composio.tools.get(toolkits=["googlesheets"])` / `["notion"]` rather than guessing.
- `connected_accounts.delete/enable/disable` all exist in the current SDK (confirmed) — decide whether `DELETE /integrations/{provider}` should delete or just disable (disable is reversible, keeps history).
- Webhook payload is V3 shape: `{id, type, metadata: {trigger_slug, connected_account_id, user_id, ...}, data, timestamp}` (confirmed) — `triggers.py` should match on `metadata.connected_account_id` + `data`, not assume the V2 `payload["data"]["connection_id"]` shape some older examples still show.
- Assumes a `User.id` already exists internally (from the auth system `API_ENDPOINTS.md` §1 specifies but that isn't built yet) and doubles as Composio's `user_id`. Flag if that's wrong.

## 8. Non-goals

No agentic tool-calling (§2). No Celery/external job queue (§4.5, per `BACKEND_SPEC.md` §2). No bulk-approve endpoint (§4.4, per `API_ENDPOINTS.md` §7's deliberate omission). No auth-config creation via API — done once via dashboard.
