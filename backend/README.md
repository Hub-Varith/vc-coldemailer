# vc-coldemailer backend

FastAPI service for the investor targeting & outreach platform. See `../AGENTS.md` and `../BRIEF.md` for product/architecture context, `../BACKEND_SPEC.md` for the pipeline contracts and `../API_ENDPOINTS.md` for the HTTP surface.

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

1. Install dependencies:

   ```bash
   cd backend
   uv sync
   ```

2. Optionally create `backend/.env`. **Every integration is optional** — with no keys the
   pipeline runs against the bundled local index and deterministic planning/extraction/drafting,
   which is what the demo uses.

   ```bash
   OCTEN_API_KEY=              # live retrieval; falls back to the local index
   OPENAI_API_KEY=             # with OPENAI_MODEL_PLANNER + OPENAI_MODEL_EXTRACTOR
   OPENAI_MODEL_PLANNER=       # pin explicitly, never hardcode a model in source
   OPENAI_MODEL_EXTRACTOR=     # smaller model — this runs hundreds of times
   COMPOSIO_API_KEY=           # Gmail/Sheets/Notion actions
   ```

   `.env` is gitignored — never commit it.

3. Run the dev server:

   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

   Served at http://localhost:8000 with routes under `/api/v1` (`GET /api/v1/health`).
   Interactive docs at http://localhost:8000/docs. On startup the service warms one run so
   the workspace opens onto data; set `WARM_RUN_ON_STARTUP=false` to disable.

## The pipeline

Six stages, streamed to `GET /runs/{id}/events` as they happen:

```
profile → search plan → parallel retrieval → evidence extraction → freshness verification → scoring → TargetList
```

A local run fans out ~520 narrow queries at concurrency 64 and returns in a few hundred
milliseconds. Rules enforced in code, not just prompts:

- a record without a `source_url` is discarded;
- a record with no date is discarded — undated evidence is not evidence;
- an investor with zero evidence is dropped from the list, not scored low;
- stale facts may be shown but never open an email;
- founder-affinity signals are a post-sort tiebreak, never a scoring term;
- nothing sends without a per-message approval, and every send needs an `Idempotency-Key`.

## Demo path

```bash
curl -X POST localhost:8000/api/v1/runs -H 'Content-Type: application/json' -d '{}'
curl "localhost:8000/api/v1/runs/<run_id>/targets?limit=10"
curl -N localhost:8000/api/v1/runs/<run_id>/events        # SSE progress
curl -X POST localhost:8000/api/v1/targets/<target_id>/draft
curl -X POST localhost:8000/api/v1/drafts/<draft_id>/approve -H 'Content-Type: application/json' -d '{"approved_by":"founder"}'
curl -X POST localhost:8000/api/v1/drafts/<draft_id>/send -H 'Idempotency-Key: demo-1'
```

`GET /runs/{id}/plan` returns the generated query fan-out — the most persuasive demo surface.

## Tests

```bash
uv run pytest
```

Tests run against recorded fixtures in `tests/fixtures/`, never the live API.
`tests/fixtures/target_list.json` is the frozen `TargetList` handoff fixture: the Composio
module can develop against it without running the pipeline.

## Adding dependencies

```bash
uv add <package>
```
