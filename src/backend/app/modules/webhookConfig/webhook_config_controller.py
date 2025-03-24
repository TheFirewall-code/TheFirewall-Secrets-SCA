from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.modules.webhookConfig.schemas.webhook_schema import (
    WebhookConfigCreate,
    WebhookConfigResponse,
    WebhookConfigDetail,
    WebhookConfigUpdate
)
from app.modules.webhookConfig.webhook_config_service import (
    create_webhook_config,
    get_webhook_config_by_vc_id,
    generate_new_secret,
    update_webhook_config,
    delete_webhook_config_by_vc_id
)
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole

router = APIRouter(
    prefix="/webhook_config",
    tags=["Version Control Webhook Config"]
)


@router.post("/", response_model=WebhookConfigResponse, 
             dependencies=[Depends(role_required([UserRole.admin]))])
async def create_webhook_config_route(
    webhook_config: WebhookConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Creates a new webhook configuration for version control.
    """
    return await create_webhook_config(db, webhook_config, current_user)


@router.get("/{vc_id}", response_model=WebhookConfigDetail,
            dependencies=[Depends(role_required([UserRole.admin]))])
async def get_webhook_config_by_vc_id_route(
    vc_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves webhook configuration details by VC ID.
    """
    return await get_webhook_config_by_vc_id(db, vc_id)


@router.post("/{vc_id}/update-secret", response_model=WebhookConfigResponse,
             dependencies=[Depends(role_required([UserRole.admin]))])
async def generate_new_secret_route(
    vc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Generates a new secret for an existing webhook configuration.
    """
    return await generate_new_secret(db, vc_id, current_user)


@router.put("/{vc_id}", response_model=WebhookConfigResponse,
            dependencies=[Depends(role_required([UserRole.admin]))])
async def update_webhook_config_route(
    vc_id: int,
    update_data: WebhookConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Updates an existing webhook configuration with new details.
    """
    return await update_webhook_config(db, vc_id, update_data, current_user)


@router.delete("/{vc_id}", response_model=WebhookConfigResponse,
               dependencies=[Depends(role_required([UserRole.admin]))])
async def delete_webhook_config_by_vc_id_route(
    vc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Deactivates a webhook configuration by VC ID.
    """
    return await delete_webhook_config_by_vc_id(db, vc_id, current_user)
