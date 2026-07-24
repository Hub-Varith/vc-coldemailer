from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db.integration import ConnectedAccount


async def create_connected_account(
    session: AsyncSession, *, user_id: str, provider: str, composio_connected_account_id: str
) -> ConnectedAccount:
    account = ConnectedAccount(
        user_id=user_id,
        provider=provider,
        composio_connected_account_id=composio_connected_account_id,
        status="pending",
    )
    session.add(account)
    await session.flush()
    return account


async def get_connected_account(
    session: AsyncSession, *, user_id: str, provider: str
) -> ConnectedAccount | None:
    result = await session.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id, ConnectedAccount.provider == provider
        )
    )
    return result.scalar_one_or_none()


async def list_connected_accounts(session: AsyncSession, *, user_id: str) -> list[ConnectedAccount]:
    result = await session.execute(
        select(ConnectedAccount).where(ConnectedAccount.user_id == user_id)
    )
    return list(result.scalars().all())


async def update_status(
    session: AsyncSession, *, account: ConnectedAccount, status: str, error_reason: str | None = None
) -> ConnectedAccount:
    account.status = status
    account.error_reason = error_reason
    await session.flush()
    return account
