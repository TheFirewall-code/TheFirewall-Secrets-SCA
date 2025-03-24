from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.modules.webhookConfig.models.webhookConfig import WebhookConfig
from app.modules.webhookConfig.schemas.webhook_schema import *
from app.utils.generateSecret import generate_secret
from app.utils.validate_git_actions import validate_git_actions
from app.modules.user.models.user import User


async def create_webhook_config(
        db: AsyncSession,
        webhook_config: WebhookConfigCreate,
        current_user: User) -> WebhookConfigResponse:
    
    # Check for existing webhook config
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.vc_id == webhook_config.vc_id))
    existing_config = result.scalars().first()
    if existing_config:
        raise HTTPException(status_code=400, detail="WebhookConfig for this VC ID already exists")

    # Generate secret and create new config
    secret = generate_secret()
    new_webhook_config = WebhookConfig(
        **webhook_config.dict(),
        secret=secret
    )

    db.add(new_webhook_config)
    await db.commit()
    await db.refresh(new_webhook_config)

    return WebhookConfigResponse(
        id=new_webhook_config.id,
        vc_type=new_webhook_config.vc_type.value,
        webhook_url=f"/webhook/{new_webhook_config.vc_type.value}/{new_webhook_config.vc_id}",
        secret=secret,
        message="Webhook added successfully!",
        active=new_webhook_config.active,
        block_message=new_webhook_config.block_message,
        unblock_message=new_webhook_config.unblock_message,
        block_pr_on_sec_found=new_webhook_config.block_pr_on_sec_found,
        block_pr_on_vul_found=new_webhook_config.block_pr_on_vul_found,
        jira_alerts_enabled=new_webhook_config.jira_alerts_enabled,
        slack_alerts_enabled=new_webhook_config.slack_alerts_enabled
    )


async def get_webhook_config_by_vc_id(
        db: AsyncSession,
        vc_id: int) -> WebhookConfigDetail:
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.vc_id == vc_id))
    config = result.scalars().first()

    if not config:
        raise HTTPException(status_code=404, detail="WebhookConfig not found")

    return WebhookConfigDetail(
        id=config.id,
        vc_id=config.vc_id,
        vc_type=config.vc_type,
        scan_type=config.scan_type,
        git_actions=config.git_actions,
        target_repos=config.target_repos,
        block_message=config.block_message,
        unblock_message=config.unblock_message,
        active=config.active,
        block_pr_on_sec_found=config.block_pr_on_sec_found,
        block_pr_on_vul_found=config.block_pr_on_vul_found,
        jira_alerts_enabled=config.jira_alerts_enabled,
        slack_alerts_enabled=config.slack_alerts_enabled,
        secret=config.secret,
        url=f"/webhook/{config.vc_type.value}/{config.vc_id}"
    )


async def generate_new_secret(
        db: AsyncSession,
        vc_id: int,
        current_user: User) -> WebhookConfigResponse:
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.vc_id == vc_id))
    config = result.scalars().first()

    if not config:
        raise HTTPException(status_code=404, detail="WebhookConfig not found")

    # Generate and update secret
    config.secret = generate_secret()
    await db.commit()
    await db.refresh(config)

    return WebhookConfigResponse(
        id=config.id,
        vc_type=config.vc_type.value,
        webhook_url=f"/webhook/{config.vc_type.value}/{config.vc_id}",
        secret=config.secret,
        message="Secret updated successfully!",
        active=config.active,
        block_message=config.block_message,
        unblock_message=config.unblock_message,
        block_pr_on_sec_found=config.block_pr_on_sec_found,
        block_pr_on_vul_found=config.block_pr_on_vul_found,
        jira_alerts_enabled=config.jira_alerts_enabled,
        slack_alerts_enabled=config.slack_alerts_enabled
    )


async def update_webhook_config(
        db: AsyncSession,
        vc_id: int,
        update_data: WebhookConfigUpdate,
        current_user: User) -> WebhookConfigResponse:
    
    # Fetch existing config
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.vc_id == vc_id))
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="WebhookConfig not found")

    # # Validate git actions if provided
    # if update_data.git_actions:
    #     if not validate_git_actions(update_data.vc_type, update_data.git_actions):
    #         raise HTTPException(status_code=400, detail="Invalid git actions for the specified vc_type")

    # Update configuration fields
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)

    return WebhookConfigResponse(
        id=config.id,
        vc_type=config.vc_type.value,
        webhook_url=f"/webhook/{config.vc_type.value}/{config.vc_id}",
        secret=config.secret,
        message="Webhook configuration updated successfully!",
        active=config.active,
        block_message=config.block_message,
        unblock_message=config.unblock_message,
        block_pr_on_sec_found=config.block_pr_on_sec_found,
        block_pr_on_vul_found=config.block_pr_on_vul_found,
        jira_alerts_enabled=config.jira_alerts_enabled,
        slack_alerts_enabled=config.slack_alerts_enabled
    )


async def delete_webhook_config_by_vc_id(
        db: AsyncSession,
        vc_id: int,
        current_user: User) -> WebhookConfigResponse:

    result = await db.execute(select(WebhookConfig).where(WebhookConfig.vc_id == vc_id))
    config = result.scalars().first()

    if not config:
        raise HTTPException(status_code=404, detail="WebhookConfig not found")

    # Deactivate webhook config
    config.active = False
    await db.commit()
    await db.refresh(config)

    return WebhookConfigResponse(
        id=config.id,
        vc_type=config.vc_type.value,
        message="Webhook configuration deleted successfully!",
        active=config.active,
        block_message=config.block_message,
        unblock_message=config.unblock_message,
        block_pr_on_sec_found=config.block_pr_on_sec_found,
        block_pr_on_vul_found=config.block_pr_on_vul_found,
        jira_alerts_enabled=config.jira_alerts_enabled,
        slack_alerts_enabled=config.slack_alerts_enabled
    )


async def disable_all_webhooks(db: AsyncSession) -> bool:
    """
    Disable all webhook configurations by setting `active = False`.
    """
    # Fetch all active webhooks
    query = select(WebhookConfig).filter(WebhookConfig.active == True)
    result = await db.execute(query)
    webhooks = result.scalars().all()

    if not webhooks:
        return True

    # Disable all webhooks
    for webhook in webhooks:
        webhook.active = False

    await db.commit()

    return True