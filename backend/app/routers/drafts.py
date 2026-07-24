"""Composio owner's routes: drafts, approval queue, sends, sequences.

OWNER: Composio (you). Edit freely — the Octen owner does not touch this file.
Build against tests/fixtures/target_list.json until the pipeline is live.

Paths mirror API_ENDPOINTS.md §6 (drafts/queue) and §7 (sending/sequences).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["drafts"])


# --- §6 Drafts & approval queue ---
@router.post("/targets/{target_id}/draft")
async def generate_draft(target_id: str) -> dict[str, str]:
    raise NotImplementedError


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str) -> dict[str, str]:
    raise NotImplementedError


@router.get("/queue")
async def approval_queue() -> dict[str, str]:
    raise NotImplementedError


# --- §7 Sending & sequences ---
@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str) -> dict[str, str]:
    raise NotImplementedError


@router.post("/drafts/{draft_id}/send")
async def send_draft(draft_id: str) -> dict[str, str]:
    # Requires Idempotency-Key header; rejects if sending_domain_verified is false.
    raise NotImplementedError
