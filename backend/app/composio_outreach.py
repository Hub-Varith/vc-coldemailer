"""In-memory Composio outreach: connect Gmail, draft, send.

No database — matches app/store.py's own in-memory precedent
(BACKEND_SPEC.md Sec 2 explicitly allows this for v1/demo scope). State is
lost on restart; that's an accepted, deliberate simplification for this
pass, not an oversight.
"""

import uuid

_gmail_connection: dict = {"status": "disconnected", "connected_account_id": None}
_drafts: dict[str, dict] = {}
_sent_idempotency_keys: set[str] = set()


def reset_state() -> None:
    """Test-only: clear all in-memory state between tests."""
    _gmail_connection["status"] = "disconnected"
    _gmail_connection["connected_account_id"] = None
    _drafts.clear()
    _sent_idempotency_keys.clear()


def connect_gmail(composio_client, *, user_id: str, auth_config_id: str, callback_url: str) -> dict:
    connection_request = composio_client.connected_accounts.initiate(
        user_id=user_id, auth_config_id=auth_config_id, callback_url=callback_url
    )
    _gmail_connection["status"] = "pending"
    _gmail_connection["connected_account_id"] = connection_request.id
    return {"redirect_url": connection_request.redirect_url, "connection_id": connection_request.id}


def gmail_status() -> str:
    return _gmail_connection["status"]


def mark_gmail_active(composio_client) -> str:
    connection_id = _gmail_connection["connected_account_id"]
    remote = composio_client.connected_accounts.get(connection_id)
    _gmail_connection["status"] = "connected" if remote.status == "ACTIVE" else "error"
    return _gmail_connection["status"]


async def draft_email(openai_client, model: str, *, contact_email: str, lead_evidence_claim: str) -> dict:
    response = await openai_client.responses.create(
        model=model,
        instructions=(
            "Draft an 80-120 word cold outreach email to an investor. Open from "
            "the single evidence fact given — do not invent additional facts."
        ),
        input=f"Lead evidence: {lead_evidence_claim}\nContact: {contact_email}",
    )
    text = response.output_text
    subject, _, body = text.partition("\n\n")
    subject = subject.removeprefix("Subject:").strip()

    draft_id = str(uuid.uuid4())
    _drafts[draft_id] = {"contact_email": contact_email, "subject": subject, "body": body.strip(), "approved": False}
    return {"draft_id": draft_id, "subject": subject, "body": body.strip()}


def approve_draft(draft_id: str) -> None:
    _drafts[draft_id]["approved"] = True


async def send_draft(composio_client, draft_id: str, idempotency_key: str) -> dict:
    if idempotency_key in _sent_idempotency_keys:
        return {"status": "already_sent"}

    if _gmail_connection["status"] != "connected":
        raise ValueError("gmail_not_connected")

    draft = _drafts[draft_id]
    if not draft["approved"]:
        raise ValueError("draft_not_approved")

    response = composio_client.tools.execute(
        "GMAIL_SEND_EMAIL",
        user_id="founder-1",
        connected_account_id=_gmail_connection["connected_account_id"],
        arguments={"recipient_email": draft["contact_email"], "subject": draft["subject"], "body": draft["body"]},
    )
    _sent_idempotency_keys.add(idempotency_key)
    return {"status": "sent", "message_id": response["data"]["id"]}
