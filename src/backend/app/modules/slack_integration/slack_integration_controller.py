from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole
from typing import Optional

from app.modules.slack_integration.slack_integration_service import (
    get_slack_integration,
    create_slack_integration,
    update_slack_integration,
    fetch_and_notify_secrets
)
from app.modules.slack_integration.schema.schemas import (
    SlackIntegrationBase,
    CreateSlackIntegration,
    UpdateSlackIntegration
)
from app.core.db import get_db

router = APIRouter(
    prefix="/slackIntegration",
    tags=["Slack Integration"]
)


@router.post("/", response_model=SlackIntegrationBase,
             dependencies=[Depends(role_required([UserRole.admin]))])
async def create_slack_integration_controller(
    slack_integration: CreateSlackIntegration,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await create_slack_integration(db, slack_integration, current_user)


@router.get("/",
            response_model=SlackIntegrationBase,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_slack_integration_controller(
    db: AsyncSession = Depends(get_db),
):
    integration = await get_slack_integration(db, mask=True)
    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Slack Integration not found")
    return integration


@router.put("/", response_model=SlackIntegrationBase,
            dependencies=[Depends(role_required([UserRole.admin]))])
async def update_slack_integration_controller(
    slack_integration: UpdateSlackIntegration,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    integration = await update_slack_integration(db, slack_integration, current_user)
    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Slack Integration not found")
    return integration


@router.post("/notify-secrets",
             dependencies=[Depends(role_required([UserRole.admin]))])
async def notify(
    number_of_secrets: int,
    repo_name: str,
    scan_type: str,
    pr_id: Optional[int] = None,
    commit_id: Optional[int] = None,
    link: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):

    return await fetch_and_notify_secrets(
        db=db,
        number_of_secrets=number_of_secrets,
        repo_name=repo_name,
        scan_type=scan_type,
        pr_id=pr_id,
        commit_id=commit_id,
        link=link
    )
