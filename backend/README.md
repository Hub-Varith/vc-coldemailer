# vc-coldemailer backend

FastAPI service for the investor targeting & outreach platform. See `../AGENTS.md` and `../BRIEF.md` for product/architecture context.

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) for dependency management

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

   # OpenAI model roles — pinned via env, never hardcoded (see BACKEND_SPEC.md §4).
   # Planner: larger model, runs once per run. Extractor: cheaper, high volume.
   OPENAI_MODEL_PLANNER=gpt-5.6-sol
   OPENAI_MODEL_EXTRACTOR=gpt-5.6-terra
   ```

   `.env` is gitignored — never commit it.

3. Run the dev server:

   ```bash
   uv run fastapi dev app/main.py
   ```

   The API is served at http://localhost:8000, with routes under `/api/` (health check: `GET /api/health`).

## Running tests

```bash
cd backend
uv run pytest
```

## Adding dependencies

```bash
uv add <package>
```
