# AGENTS.md

This file provides guidance to coding agents (Claude Code, etc.) when working with code in this repository.

## What this is

An investor targeting & outreach platform: a founder describes their company and round once, and the platform returns a ranked list of ~60–80 investors, each backed by timestamped evidence, with a personalized draft email queued for human approval.

Three docs define the system — read the relevant one before making decisions:

- `BRIEF.md` — product spec; defines the non-negotiable product rules below.
- `BACKEND_SPEC.md` — implementation spec for the backend: repo layout, the Octen retrieval module (client/planner/executor/extractor/verifier/scorer), the OpenAI layer, Pydantic models, the `TargetList` contract handed to the Composio module, and the milestone order (M1–M6) to build in.
- `API_ENDPOINTS.md` — the frontend↔backend HTTP contract (`/api/v1`): auth, integrations, profiles, runs (with SSE progress events), targets, drafts/approval queue, sending & sequences, replies/pipeline.

Non-negotiable product rules:

- **Nothing sends autonomously.** Every email requires human approval.
- **No evidence, no listing.** No investor enters a list without at least one retrievable, dated piece of evidence.
- **Hard list cap (~80)** and **own-domain sending only**.
- The core design principle: the evidence that qualifies an investor and the personalization in the email are the same artifact — one retrieval pass produces the score, the proof, and the draft.

## Architecture

Three external layers (see BRIEF.md §8):

- **Octen** — high-concurrency real-time search for parallel retrieval (the fan-out in the pipeline). Note: API access was invitation-only; confirm availability before building against it.
- **Composio** — authenticated account actions: Gmail history lookup, drafts, sends, Sheets/Notion logging, follow-up scheduling. Client is created in `backend/app/composio_client.py` (cached via `lru_cache`, requires `COMPOSIO_API_KEY` env var).
- **LLM layer** — search planning, evidence extraction into schema, draft writing. Kept deliberately narrow: retrieval does the heavy lifting.

The pipeline (BRIEF.md §5): profile → structured search plan → parallel retrieval → dated evidence extraction → freshness re-verification → scoring (evidence strength + recency; founder-affinity signals are tiebreakers only) → draft generation → approval queue → send & follow-up sequence.

## Codebase

- `backend/` — FastAPI app managed with **uv** (Python ≥3.12). App code lives in `backend/app/`; `main.py` holds the FastAPI instance with routes under `/api/`.
- No frontend, tests, or linter configured yet.

## Commands

All backend commands run from `backend/`:

```bash
uv sync                       # install dependencies
uv run fastapi dev app/main.py  # run dev server (http://localhost:8000)
uv add <package>              # add a dependency
```

`COMPOSIO_API_KEY` must be set in the environment for any Composio-touching code path.
