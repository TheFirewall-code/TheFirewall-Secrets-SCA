from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.webhook.webhook_service import process_webhook

router = APIRouter(prefix="/webhook", tags=["Pull Request"])


@router.post("/{vc_type}/{vc_id}")
async def process_pr_webhook(
    vc_type: str,
    vc_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await process_webhook(vc_type, vc_id, request, db, background_tasks)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error processing webhook: {str(e)}"
        )
