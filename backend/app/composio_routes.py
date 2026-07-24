"""Composio owner's routes. Adds exactly one line to app/main.py
(app.include_router(router)) — everything else lives here."""

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.composio_client import get_composio
from app.composio_outreach import (
    approve_draft,
    draft_email,
    gmail_status,
    connect_gmail,
    mark_gmail_active,
    send_draft,
)
from app.openai_client import get_openai

router = APIRouter(prefix="/api/v1")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


@router.post("/integrations/gmail/connect")
def connect(composio_client=Depends(get_composio)):
    return connect_gmail(
        composio_client,
        user_id="founder-1",
        auth_config_id=_require("COMPOSIO_AUTH_CONFIG_GMAIL"),
        callback_url=_require("COMPOSIO_CALLBACK_URL"),
    )


@router.get("/integrations/gmail/status")
def status(composio_client=Depends(get_composio)):
    if gmail_status() == "pending":
        mark_gmail_active(composio_client)
    return {"status": gmail_status()}


class DraftRequest(BaseModel):
    contact_email: str
    lead_evidence_claim: str


@router.post("/targets/{target_id}/draft")
async def create_draft(target_id: str, body: DraftRequest, openai_client=Depends(get_openai)):
    return await draft_email(
        openai_client,
        _require("OPENAI_MODEL_DRAFTER"),
        contact_email=body.contact_email,
        lead_evidence_claim=body.lead_evidence_claim,
    )


@router.post("/drafts/{draft_id}/approve")
def approve(draft_id: str):
    try:
        approve_draft(draft_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": {"code": "draft_not_found"}})
    return {"draft_id": draft_id, "status": "approved"}


@router.post("/drafts/{draft_id}/send")
async def send(draft_id: str, composio_client=Depends(get_composio), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "idempotency_key_required"}})
    try:
        return await send_draft(composio_client, draft_id, idempotency_key)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"error": {"code": str(e)}})
