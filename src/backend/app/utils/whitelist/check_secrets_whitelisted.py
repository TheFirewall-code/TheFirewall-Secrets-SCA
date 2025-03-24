from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_
from sqlalchemy.future import select
from app.modules.secrets.secret_service import Secrets

async def check_secrets_whitelisted(db: AsyncSession, pr_scan_id: int) -> bool:
    query = select(func.count()).select_from(Secrets).where(
        and_(Secrets.pr_scan_id == pr_scan_id, Secrets.whitelisted == False)
    )
    result = await db.scalar(query)
    return result == 0