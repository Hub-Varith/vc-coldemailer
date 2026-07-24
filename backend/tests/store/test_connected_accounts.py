import pytest

from app.composio_store.connected_accounts import (
    create_connected_account,
    get_connected_account,
    list_connected_accounts,
    update_status,
)


async def test_create_and_get_connected_account(db_session):
    created = await create_connected_account(
        db_session,
        user_id="founder-1",
        provider="gmail",
        composio_connected_account_id="ca_abc123",
    )
    await db_session.commit()

    fetched = await get_connected_account(db_session, user_id="founder-1", provider="gmail")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.status == "pending"
    assert fetched.composio_connected_account_id == "ca_abc123"


async def test_get_connected_account_returns_none_when_missing(db_session):
    assert await get_connected_account(db_session, user_id="founder-1", provider="notion") is None


async def test_list_connected_accounts_scopes_by_user(db_session):
    await create_connected_account(
        db_session, user_id="founder-1", provider="gmail", composio_connected_account_id="ca_1"
    )
    await create_connected_account(
        db_session, user_id="founder-2", provider="gmail", composio_connected_account_id="ca_2"
    )
    await db_session.commit()

    accounts = await list_connected_accounts(db_session, user_id="founder-1")
    assert [a.provider for a in accounts] == ["gmail"]


async def test_update_status_sets_status_and_error_reason(db_session):
    account = await create_connected_account(
        db_session, user_id="founder-1", provider="gmail", composio_connected_account_id="ca_1"
    )
    await db_session.commit()

    updated = await update_status(db_session, account=account, status="error", error_reason="oauth_denied")
    await db_session.commit()

    assert updated.status == "error"
    assert updated.error_reason == "oauth_denied"
