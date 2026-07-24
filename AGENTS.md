# AGENTS.md

This file provides guidance to coding agents (Claude Code, etc.) when working with code in this repository.

## What this is

An investor targeting & outreach platform: a founder describes their company and round once, and the platform returns a ranked list of ~60–80 investors, each backed by timestamped evidence, with a personalized draft email queued for human approval. Read `BRIEF.md` before making product decisions — it is the spec and defines non-negotiable product rules:

- **Nothing sends autonomously.** Every email requires human approval.
- **No evidence, no listing.** No investor enters a list without at least one retrievable, dated piece of evidence.
- **Hard list cap (~80)** and **own-domain sending only**.
- The core design principle: the evidence that qualifies an investor and the personalization in the email are the same artifact — one retrieval pass produces the score, the proof, and the draft.

`BACKEND_SPEC.md` (pipeline + module contracts) and `API_ENDPOINTS.md` (HTTP surface, base path `/api/v1`) are the implementation specs. Follow them over improvisation.

## Architecture

Three external layers (see BRIEF.md §8), all of them optional at runtime:

- **Octen** — high-concurrency real-time search. `backend/app/octen/client.py` is the ONLY module that touches Octen's wire format; fix mappings there and nowhere else. With no `OCTEN_API_KEY`, `LocalIndexClient` serves the bundled corpus through the same contract.
- **OpenAI** — planning, extraction, drafting. `app/llm.py` wraps `openai_client.get_openai()` with strict JSON-schema structured outputs and a token ledger. Without keys, every call site falls back to a deterministic path, so the pipeline always terminates.
- **Composio** — Gmail/Sheets/Notion account actions in `app/composio_client.py`. Without a key, sends are recorded locally and marked `local.no_provider`.

Pipeline (`app/pipeline.py`), six stages, each streamed to the SSE bus: plan → retrieve → extract → verify → score → publish.

| Stage | Module | Rule it enforces |
|---|---|---|
| Plan | `octen/planner.py` | breadth — 150–400 narrow queries across six intents |
| Retrieve | `octen/executor.py` | dedupe, semaphore fan-out, TTL cache, timing; a failed query is a dropped data point, never a failed run |
| Extract | `octen/extractor.py` | no `source_url` → discard; no date → discard. Undated evidence is not evidence |
| Verify | `octen/verifier.py` | per-type staleness thresholds; stale facts may show but never open an email |
| Score | `octen/scorer.py` | strength × recency × kind weight; affinity is a post-sort nudge, never a scoring term |
| Draft | `outreach/drafting.py` | 80–120 words from `lead_evidence`; stale lead ⇒ `needs_review`, not a draft |
| Send | `outreach/sending.py` | per-message approval required, `Idempotency-Key` required, domain must be verified |

## Codebase

- `backend/` — FastAPI managed with **uv** (Python ≥3.12). Routes under `/api/v1` in `app/routers/`; models are Pydantic in `app/models/` (no dicts cross module boundaries). Storage is `app/store/repo.py` — one seam to swap for SQLAlchemy.
- `frontend/` — Vite + React + TypeScript + Tailwind v4 + Framer Motion + Lucide. Single-screen workspace: ranked list → dated evidence → editable draft → approve & queue. `src/data/offlineSnapshot.ts` is a captured real run so the UI still demonstrates the flow when the API is down.

## Commands

```bash
# backend (from backend/)
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest

# frontend (from frontend/)
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
npm run typecheck
npm run build
```

Optional env in `backend/.env` — all absent is a valid configuration: `OCTEN_API_KEY`, `OPENAI_API_KEY` + `OPENAI_MODEL_PLANNER` + `OPENAI_MODEL_EXTRACTOR`, `COMPOSIO_API_KEY`.
