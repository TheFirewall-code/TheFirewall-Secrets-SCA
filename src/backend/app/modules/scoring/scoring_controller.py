from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.auth.auth_utils import role_required
from app.modules.user.models.user import UserRole
from typing import List, Dict
from app.modules.scoring.scoring_service import ScoringService
from app.modules.scoring.scoring_cron import calculate_score

router = APIRouter(prefix="/scoring", tags=["Scoring"])


@router.get("/secret/{secret_id}/score")
async def get_secret_score(secret_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get the score for a specific secret by ID.
    """
    score = await ScoringService.calculate_secret_score_by_id(db, secret_id)
    return {"secret_id": secret_id, "score": score}

@router.get("/vulnerability/{vulnerability_id}/score")
async def get_secret_score(vulnerability_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get the score for a specific secret by ID.
    """
    score = await ScoringService.calculate_vul_score_by_id(db, vulnerability_id)
    return {"vulnerability_id": vulnerability_id, "score": score}


@router.get("/repo/{repo_id}/score")
async def get_repo_score(repo_id: int, db: AsyncSession = Depends(get_db)):
    score = await ScoringService.calculate_repo_score_from_normailzed_secret(db, repo_id)
    return {"repo_id": repo_id, "score": score}


@router.get("/group/{group_id}/score")
async def get_group_score(group_id: int, db: AsyncSession = Depends(get_db)):
    score = await ScoringService.calculate_group_score_from_normalized_secret(db, group_id)
    return {"group_id": group_id, "score": score}


@router.post("/run-cron")
async def runCron(db: AsyncSession = Depends(get_db)):
    return await calculate_score(db)
