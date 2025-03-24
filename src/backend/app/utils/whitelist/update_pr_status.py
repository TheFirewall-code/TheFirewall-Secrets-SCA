from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

import requests

# FastAPI and Typing Imports
from fastapi import HTTPException
from app.modules.pr.models.pr_scan import PRScan
from app.modules.vc.models.vc import VcTypes
from app.modules.vc.vc_service import get_vc
from app.utils.secret_scanning.build_headers import build_headers
from app.utils.secret_scanning.handle_pr_actions import update_pr_status as update_pr_status_global


async def update_pr_status(db: AsyncSession, pr_scan_id: int, unblock: bool):
    print("Whitelisting secret")
    stmt = select(PRScan).where(PRScan.id == pr_scan_id)
    pr_scan = await db.scalars(stmt)
    pr_scan = pr_scan.first()

    vc = await get_vc(db=db, vc_id=pr_scan.vc_id)
    await update_pr_status_global(vc.type, vc.token, pr_scan.stat_url, 0, 0, unblock=unblock)