import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .errors import ApiError, api_error_handler, http_exception_handler, validation_exception_handler
from .routers import account, demo, drafts, profiles, runs, sends, system, targets
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed()
    if get_settings().warm_run_on_startup:
        # The store is in-memory, so a restart would otherwise open onto an empty
        # workspace. Warm one run so the list is populated the moment the UI loads.
        import asyncio

        from .models import Run
        from .pipeline import PIPELINE
        from .seed import DEMO_PROFILE
        from .store.repo import REPO

        run = Run(profile_id=DEMO_PROFILE.id)
        await REPO.save_run(run)
        asyncio.create_task(PIPELINE.run(run, DEMO_PROFILE))
    yield


app = FastAPI(
    title="Proofline API",
    version="0.1.0",
    description="Live, verified investor targeting. Every name arrives with dated evidence.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

for router in (
    system.router,
    account.router,
    profiles.router,
    runs.router,
    targets.router,
    drafts.router,
    sends.router,
    demo.router,
):
    app.include_router(router, prefix=API_PREFIX)


@app.get("/api/health")
def legacy_health() -> dict[str, str]:
    return {"status": "ok"}


# In a bundled deployment the built SPA sits next to this package; serving it from the
# same origin keeps the API and the workspace on one host with no CORS or routing split.
_SPA_DIR = Path(__file__).resolve().parents[2] / "api" / "static"
if _SPA_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_SPA_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        candidate = _SPA_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_SPA_DIR / "index.html")
