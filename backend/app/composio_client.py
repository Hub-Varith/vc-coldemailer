import asyncio
import os
from functools import lru_cache
from typing import Any

from composio import Composio


@lru_cache
def get_composio() -> Composio:
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        raise RuntimeError("COMPOSIO_API_KEY is not set")
    return Composio(api_key=api_key)


def _user_id() -> str:
    return os.environ.get("COMPOSIO_USER_ID", "founder@noviaudio.com")


async def _execute(tool: str, arguments: dict[str, Any]) -> Any:
    """Composio's SDK is sync; keep the pipeline's no-blocking-calls rule intact."""
    return await asyncio.to_thread(
        lambda: get_composio().tools.execute(tool, user_id=_user_id(), arguments=arguments)
    )


async def send_email(to: str, subject: str, body: str, from_email: str) -> Any:
    return await _execute(
        "GMAIL_SEND_EMAIL",
        {"recipient_email": to, "subject": subject, "body": body, "user_id": from_email},
    )


async def find_prior_threads(query: str, max_results: int = 5) -> Any:
    return await _execute("GMAIL_FETCH_EMAILS", {"query": query, "max_results": max_results})


async def append_row(spreadsheet_id: str, values: list[list[str]]) -> Any:
    return await _execute(
        "GOOGLESHEETS_BATCH_UPDATE",
        {"spreadsheet_id": spreadsheet_id, "values": values, "first_cell_location": "A1"},
    )


async def create_notion_page(parent_id: str, title: str, content: str) -> Any:
    return await _execute(
        "NOTION_CREATE_NOTION_PAGE",
        {"parent_id": parent_id, "title": title, "content": content},
    )
