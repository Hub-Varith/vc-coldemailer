# vc-coldemailer backend

FastAPI service for the investor targeting & outreach platform. See
`../AGENTS.md` and `../BRIEF.md` for product/architecture context, and
`../BACKEND_SPEC.md` for the pipeline this implements.

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) for dependency management

## Layout

```
app/
  main.py          FastAPI routes
  config.py        Settings (Octen + scoring config, env / .env)
  models.py        every Pydantic model that crosses a module boundary
  octen_client.py  the only file that knows Octen's wire format
  openai_client.py OpenAI client + pinned model names (get_planner_model/get_extractor_model)
  planner.py       CompanyProfile -> SearchPlan (OpenAI)
  executor.py      SearchPlan -> RetrievalBundle (concurrent Octen fan-out)
  extractor.py     RetrievalBundle -> InvestorRecord[] (OpenAI, discard rules)
  verifier.py      freshness re-check pass, per-kind staleness thresholds
  scorer.py        scoring, ranking, list cap, founder-context tiebreaker
  pipeline.py      orchestrates the stages above end to end
  store.py         in-memory run/profile persistence
  composio_client.py  Composio SDK handle (owned by the Composio module -- see docs/superpowers/specs/2026-07-23-composio-integration-design.md)
tests/
  fixtures/        recorded Octen responses + the frozen TargetList example
```

Flatter than the nested `octen/` + `models/` package layout sketched in
`BACKEND_SPEC.md` Section 3 -- one file per pipeline stage, one
`models.py` for every contract, so the whole pipeline is readable without
hopping through subpackages.

## Setup

1. Install dependencies:

   ```bash
   cd backend
   uv sync
   ```

2. Create `backend/.env` with the required secrets:

   ```bash
   COMPOSIO_API_KEY=your-composio-api-key
   OPENAI_API_KEY=your-openai-api-key
   OCTEN_API_KEY=your-octen-api-key

   # OpenAI model roles -- pinned via env, never hardcoded (see BACKEND_SPEC.md §4).
   # Planner: larger model, runs once per run. Extractor: cheaper, high volume.
   OPENAI_MODEL_PLANNER=gpt-5.6-sol
   OPENAI_MODEL_EXTRACTOR=gpt-5.6-terra
   ```

   See `.env.example` for the full list of Octen/scoring knobs. `.env` is
   gitignored -- never commit it.

3. Run the dev server:

   ```bash
   uv run fastapi dev app/main.py
   ```

   The API is served at http://localhost:8000, with routes under `/api/`
   (health check: `GET /api/health`) plus the pipeline routes below.

## Running tests

```bash
cd backend
uv run pytest
```

Tests run entirely against recorded fixtures (`tests/fixtures/`) and mocked
OpenAI/Octen clients -- no live API keys required.

## Adding dependencies

```bash
uv add <package>
```

## API

Routes live under `/api/v1`, following `../API_ENDPOINTS.md`. This backend
implements its own slice of that contract -- profiles, runs, targets,
system health/usage. Auth, integrations, drafts/approval, sending &
sequences, replies, and export destinations are the Composio module's
routes (see `docs/superpowers/specs/2026-07-23-composio-integration-design.md`)
and are not implemented here.

```
GET    /api/v1/health
GET    /api/v1/usage                       runs/queries tracked so far (token spend not tracked yet)

POST   /api/v1/profiles
GET    /api/v1/profiles
GET    /api/v1/profiles/{id}
PATCH  /api/v1/profiles/{id}
DELETE /api/v1/profiles/{id}
POST   /api/v1/profiles/{id}/validate      cheap pre-flight check before spending a run

POST   /api/v1/runs                        202 + {run_id, status} -- backgrounded
GET    /api/v1/runs                        ?profile_id= filter, newest first
GET    /api/v1/runs/{id}                   stage, status, progress, retrieval_stats, warnings
GET    /api/v1/runs/{id}/events            SSE: stage_changed / run_complete (single-subscriber)
POST   /api/v1/runs/{id}/cancel            cooperative -- takes effect at the next stage boundary
POST   /api/v1/runs/{id}/reverify          re-run verify + score only, reusing extracted evidence
DELETE /api/v1/runs/{id}
GET    /api/v1/runs/{id}/plan              the SearchPlan (debug/demo -- shows the query fan-out)

GET    /api/v1/runs/{id}/targets           paginated, filterable (status/min_score/has_email/stale), sortable
GET    /api/v1/runs/{id}/targets/export    CSV
GET    /api/v1/targets/{id}                full evidence array
PATCH  /api/v1/targets/{id}                status / notes / contact_email override
POST   /api/v1/targets/{id}/dismiss
```

Errors come back as `{"error": {"code", "message", "details"}}`, never a
bare string, per API_ENDPOINTS.md's conventions.

## Composio handoff

`tests/fixtures/target_list_example.json` is a schema-valid `TargetList`
the Composio module owner can develop against without running the
pipeline. `tests/test_target_list_contract.py` fails if the schema drifts
from that fixture.
