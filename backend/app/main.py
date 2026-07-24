from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import get_engine
from app.models_db.base import Base
from app.routers import drafts, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="VC Cold Emailer API", lifespan=lifespan)

# Each owner registers routes in their own router file so nobody edits main.py
# once this is set up. Add new routers here as one-line includes.
app.include_router(runs.router)
app.include_router(drafts.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
