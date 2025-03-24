from sqlalchemy.future import select
from sqlalchemy import update, insert, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List
from app.modules.secrets.secret_service import Secrets
from app.modules.incidents.models.incident_model import Incidents, IncidentStatusEnum, IncidentClosedBy
from app.modules.incidents.models.activity_model import Activity, Action
from app.utils.whitelist.check_secrets_whitelisted import check_secrets_whitelisted
from app.utils.whitelist.update_pr_status import update_pr_status
from app.core.logger import logger
from app.modules.whitelist.model.whitelist_model import Whitelist


async def add_secret_str(
    db: AsyncSession,
    whitelist: Whitelist
) -> int:
    """
    Whitelist secrets according to a Whitelist object, mirroring the style of add_vulnerability_str.
    """
    name = whitelist.name
    repos = whitelist.repos or []
    vcs = whitelist.vcs or []
    is_global = whitelist.global_
    active = whitelist.active
    wl_id = whitelist.id
    user_id = whitelist.created_by

    logger.info(f"Starting secret whitelisting for whitelist id={wl_id}")

    conditions = []
    if name:
        conditions.append(Secrets.secret == name)
    if not is_global:
        if repos:
            conditions.append(Secrets.repository_id.in_(repos))
        if vcs:
            conditions.append(Secrets.vc_id.in_(vcs))
    update_stmt = update(Secrets)
    if conditions:
        update_stmt = update_stmt.where(and_(*conditions))
    update_stmt = update_stmt.values(whitelisted=active, whitelist_id=wl_id)
    await db.execute(update_stmt)
    logger.info("Executed UPDATE statement to set secrets as whitelisted.")

    filter_for_select = []
    if conditions:
        filter_for_select.append(and_(*conditions))
    filter_for_select.append(Secrets.whitelisted == active)
    filter_for_select.append(Secrets.whitelist_id == wl_id)

    query_for_ids = select(Secrets.id).where(and_(*filter_for_select))
    secret_ids = await db.scalars(query_for_ids)
    secret_ids_list = secret_ids.all()

    logger.info(f"Whitelisted secrets: {secret_ids_list}")

    if not secret_ids_list:
        logger.warning("No secrets matched the whitelist criteria.")
        await db.commit()
        return 0

    # Close incidents for these secrets
    incident_stmt = (
        update(Incidents)
        .where(
            Incidents.secret_id.in_(secret_ids_list),
            Incidents.closed_by.is_(None)
        )
        .values(
            status=IncidentStatusEnum.CLOSED,
            closed_by=IncidentClosedBy.PROGRAM
        )
    )
    await db.execute(incident_stmt)
    logger.info(f"Closed incidents for secrets: {secret_ids_list}")

    # Log activity
    incidents = await db.scalars(
        select(Incidents).where(Incidents.secret_id.in_(secret_ids_list))
    )
    for incident in incidents.all():
        await db.execute(
            insert(Activity).values(
                action=Action.INCIDENT_CLOSED,
                old_value=str(IncidentStatusEnum.OPEN),
                new_value=str(IncidentStatusEnum.CLOSED),
                incident_id=incident.id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
        )
        logger.debug(f"Logged activity for closed incident={incident.id}")

    await db.commit()
    logger.info("Committed changes after closing incidents.")

    # Update PR status
    pr_scans = await db.scalars(
        select(Secrets.pr_scan_id)
        .where(Secrets.id.in_(secret_ids_list))
        .distinct()
    )
    for pr_scan_id in pr_scans.all():
        if pr_scan_id is not None:
            all_whitelisted = await check_secrets_whitelisted(db, pr_scan_id)
            if all_whitelisted:
                await update_pr_status(db, pr_scan_id, unblock=True)
                logger.info(f"Updated PR scan {pr_scan_id} status to unblocked.")

    logger.info("Finished secret whitelisting process.")
    return len(secret_ids_list)