import logging
from sqlalchemy.future import select
from sqlalchemy import update, and_, null, insert
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from fastapi import HTTPException
from typing import Optional, List
from app.modules.secrets.secret_service import Secrets
from app.modules.incidents.models.incident_model import Incidents, IncidentStatusEnum, IncidentClosedBy
from app.modules.incidents.models.activity_model import Activity, Action
from app.utils.whitelist.check_secrets_whitelisted import check_secrets_whitelisted
from app.utils.whitelist.update_pr_status import update_pr_status
from app.core.logger import logger

import logging
from sqlalchemy import select, update, and_, or_, null, insert
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from fastapi import HTTPException
from typing import Optional, List

from app.modules.secrets.secret_service import Secrets
from app.modules.incidents.models.incident_model import Incidents, IncidentStatusEnum, IncidentClosedBy
from app.modules.incidents.models.activity_model import Activity, Action
from app.utils.whitelist.check_secrets_whitelisted import check_secrets_whitelisted
from app.utils.whitelist.update_pr_status import update_pr_status
from app.modules.vulnerability.models.vulnerability_model import Vulnerability

logger = logging.getLogger(__name__)

async def update_secret(
    db: AsyncSession,
    whitelist_id: int,
    active: bool,
    repos: Optional[List[int]],
    vcs: List[int],
    is_global: bool
) -> int:
    """
    Update secrets tied to the given whitelist:
      - If is_global=True, we filter by vc_id in vcs.
      - If is_global=False, we filter by vc_id in vcs and repository_id in repos.
      - We set whitelisted=active, whitelist_id=whitelist_id for matching secrets.
      - We remove whitelisted status for secrets that no longer match these conditions.
      - If active=False, we reopen any incidents that were previously closed by the program.
      - We update PR statuses accordingly.
      - Returns the number of secrets updated in the final statement.
    """

    logger.info(
        "Starting update_secret with whitelist_id=%s, active=%s, is_global=%s, repos=%s, vcs=%s",
        whitelist_id, active, is_global, repos, vcs
    )

    # ------------------------------------------------------
    # 1) Build conditions for secrets that SHOULD be whitelisted
    # ------------------------------------------------------
    conditions = []
    if vcs:
        conditions.append(Secrets.vc_id.in_(vcs))

    if not is_global:
        if not repos:
            logger.error("No repositories provided for non-global whitelist update.")
            raise HTTPException(
                status_code=400,
                detail="No repositories provided for non-global whitelist update."
            )
        conditions.append(Secrets.repository_id.in_(repos))

    # ------------------------------------------------------
    # 2) Whitelist the secrets that match the conditions
    # ------------------------------------------------------
    whitelist_stmt = update(Secrets)
    if conditions:
        whitelist_stmt = whitelist_stmt.where(and_(*conditions))
    whitelist_stmt = whitelist_stmt.values(
        whitelisted=active,
        whitelist_id=whitelist_id
    )
    result = await db.execute(whitelist_stmt)
    logger.info("Whitelisted secrets matching conditions. Rows affected: %s", result.rowcount)

    # ------------------------------------------------------
    # 3) Un-whitelist secrets that NO longer match, but had this whitelist_id
    # ------------------------------------------------------
    # This ensures if the user removed some repos from the list or changed `vcs`,
    # those secrets are no longer whitelisted.
    unwhitelist_conditions = []
    unwhitelist_conditions.append(Secrets.whitelist_id == whitelist_id)
    if conditions:
        # Secrets that do NOT match the new conditions
        # (we can use NOT(and_(*conditions))) or a sub-select approach
        from sqlalchemy.sql import not_
        unwhitelist_conditions.append(not_(and_(*conditions)))

    unwhitelist_stmt = (
        update(Secrets)
        .where(and_(*unwhitelist_conditions))
        .values(
            whitelisted=False,
            whitelist_id=null()
        )
    )
    unwhitelist_result = await db.execute(unwhitelist_stmt)
    logger.info("Un-whitelisted secrets that no longer match conditions. Rows affected: %s", unwhitelist_result.rowcount)

    # ------------------------------------------------------
    # 4) If active=False, we reopen incidents closed by PROGRAM for these secrets
    # ------------------------------------------------------
    if not active:
        secret_ids = await db.scalars(
            select(Secrets.id).where(Secrets.whitelist_id == whitelist_id)
        )
        secret_ids_list = secret_ids.all()
        logger.info("Found %d secrets for inactive whitelist. Re-opening incidents if needed.", len(secret_ids_list))

        if secret_ids_list:
            reopen_stmt = (
                update(Incidents)
                .where(
                    and_(
                        Incidents.secret_id.in_(secret_ids_list),
                        Incidents.status == IncidentStatusEnum.CLOSED,
                        Incidents.closed_by == IncidentClosedBy.PROGRAM
                    )
                )
                .values(
                    status=IncidentStatusEnum.OPEN,
                    closed_by=None
                )
            )
            await db.execute(reopen_stmt)
            logger.info("Reopened incidents for secrets: %s", secret_ids_list)

            # Log activity for reopened incidents
            incidents = await db.scalars(
                select(Incidents).where(
                    and_(
                        Incidents.secret_id.in_(secret_ids_list),
                        Incidents.status == IncidentStatusEnum.OPEN
                    )
                )
            )
            for incident in incidents.all():
                activity_stmt = insert(Activity).values(
                    action=Action.INCIDENT_OPENED,
                    old_value=str(IncidentStatusEnum.CLOSED),
                    new_value=str(IncidentStatusEnum.OPEN),
                    incident_id=incident.id,
                    created_at=datetime.utcnow()
                )
                await db.execute(activity_stmt)
                logger.debug("Logged activity for reopened incident_id=%s", incident.id)

    # ------------------------------------------------------
    # 5) Update PR statuses
    # ------------------------------------------------------
    # For all secrets with the current whitelist_id,
    # if active=True, check if fully whitelisted; if false, block the PR.
    secrets_after_update = await db.scalars(
        select(Secrets).where(Secrets.whitelist_id == whitelist_id)
    )
    for secret in secrets_after_update.all():
        if secret.pr_scan_id:
            if active:
                all_whitelisted = await check_secrets_whitelisted(db, secret.pr_scan_id)
                if all_whitelisted:
                    await update_pr_status(db, secret.pr_scan_id, unblock=True)
                    logger.info("PR scan %s unblocked (all secrets whitelisted).", secret.pr_scan_id)
            else:
                await update_pr_status(db, secret.pr_scan_id, unblock=False)
                logger.info("PR scan %s blocked (whitelist is inactive).", secret.pr_scan_id)

    # ------------------------------------------------------
    # 6) Commit changes and return
    # ------------------------------------------------------
    await db.commit()
    logger.info("Secrets and related incidents updated successfully for whitelist_id=%s.", whitelist_id)

    # result.rowcount from the main "whitelist_stmt" is typically the # of secrets matched,
    # but keep in mind rowcount can be None in some drivers or if it's not supported.
    return result.rowcount if result.rowcount is not None else 0



async def update_vulnerability(
    db: AsyncSession,
    whitelist_id: int,
    active: Optional[bool],
    repos: Optional[List[int]],
    vcs: Optional[List[int]],
    is_global: Optional[bool]
) -> int:
    """
    Update vulnerabilities tied to the given whitelist:
      - If is_global=True, filter by vc_id in vcs.
      - If is_global=False, filter by vc_id in vcs and repository_id in repos.
      - Set whitelisted=active, whitelist_id=whitelist_id for matching vulnerabilities.
      - Un-whitelist vulnerabilities that no longer match.
      - If active=False, reopen incidents closed by the program.
      - Update PR statuses accordingly.
      - Returns the number of rows updated in the final statement.
    """

    logger.info(
        "Starting update_vulnerability with whitelist_id=%s, active=%s, is_global=%s, repos=%s, vcs=%s",
        whitelist_id, active, is_global, repos, vcs
    )

    # ------------------------------------------------------
    # 1) Build conditions for vulnerabilities that SHOULD be whitelisted
    # ------------------------------------------------------
    conditions = []
    if vcs:
        conditions.append(Vulnerability.vc_id.in_(vcs))

    if not is_global:
        if not repos:
            logger.error("No repositories provided for non-global whitelist update.")
            raise HTTPException(
                status_code=400,
                detail="No repositories provided for non-global whitelist update."
            )
        conditions.append(Vulnerability.repository_id.in_(repos))

    # ------------------------------------------------------
    # 2) Whitelist the vulnerabilities that match these conditions
    # ------------------------------------------------------
    whitelist_stmt = update(Vulnerability)
    if conditions:
        whitelist_stmt = whitelist_stmt.where(and_(*conditions))
    whitelist_stmt = whitelist_stmt.values(
        whitelisted=active,
        whitelist_id=whitelist_id
    )
    result = await db.execute(whitelist_stmt)
    logger.info("Whitelisted vulnerabilities. Rows affected: %s", result.rowcount)

    # ------------------------------------------------------
    # 3) Un-whitelist vulnerabilities no longer matching
    # ------------------------------------------------------
    unwhitelist_conditions = [Vulnerability.whitelist_id == whitelist_id]

    if conditions:
        from sqlalchemy.sql import not_
        unwhitelist_conditions.append(not_(and_(*conditions)))

    unwhitelist_stmt = (
        update(Vulnerability)
        .where(and_(*unwhitelist_conditions))
        .values(
            whitelisted=False,
            whitelist_id=null()
        )
    )
    unwhitelist_result = await db.execute(unwhitelist_stmt)
    logger.info(
        "Un-whitelisted vulnerabilities no longer matching conditions. Rows affected: %s",
        unwhitelist_result.rowcount
    )

    # ------------------------------------------------------
    # 4) If active=False, reopen incidents previously closed by PROGRAM
    # ------------------------------------------------------
    if not active:
        vuln_ids = await db.scalars(
            select(Vulnerability.id).where(Vulnerability.whitelist_id == whitelist_id)
        )
        vulnerability_ids_list = vuln_ids.all()
        logger.info(
            "Found %d vulnerabilities for inactive whitelist. Checking if we need to reopen incidents.",
            len(vulnerability_ids_list)
        )

        if vulnerability_ids_list:
            reopen_stmt = (
                update(Incidents)
                .where(
                    and_(
                        Incidents.vulnerability_id.in_(vulnerability_ids_list),
                        Incidents.status == IncidentStatusEnum.CLOSED,
                        Incidents.closed_by == IncidentClosedBy.PROGRAM
                    )
                )
                .values(
                    status=IncidentStatusEnum.OPEN,
                    closed_by=None
                )
            )
            await db.execute(reopen_stmt)
            logger.info("Reopened incidents for vulnerabilities: %s", vulnerability_ids_list)

            incidents = await db.scalars(
                select(Incidents).where(
                    and_(
                        Incidents.vulnerability_id.in_(vulnerability_ids_list),
                        Incidents.status == IncidentStatusEnum.OPEN
                    )
                )
            )
            for incident in incidents.all():
                activity_stmt = insert(Activity).values(
                    action=Action.INCIDENT_OPENED,
                    old_value=str(IncidentStatusEnum.CLOSED),
                    new_value=str(IncidentStatusEnum.OPEN),
                    incident_id=incident.id,
                    created_at=datetime.utcnow()
                )
                await db.execute(activity_stmt)
                logger.debug("Logged activity for reopened incident_id=%s", incident.id)

    # ------------------------------------------------------
    # 5) Update PR statuses if needed
    # ------------------------------------------------------
    # For vulnerabilities still having this whitelist_id,
    # if active=True, check if entire PR is whitelisted; if not, block PR.
    vulns_after_update = await db.scalars(
        select(Vulnerability).where(Vulnerability.whitelist_id == whitelist_id)
    )
    for vuln in vulns_after_update.all():
        if vuln.pr_scan_id:
            if active:
                all_whitelisted = await check_vulnerabilities_whitelisted(db, vuln.pr_scan_id)
                if all_whitelisted:
                    await update_pr_status(db, vuln.pr_scan_id, unblock=True)
                    logger.info("PR scan %s unblocked (all vulnerabilities whitelisted).", vuln.pr_scan_id)
            else:
                await update_pr_status(db, vuln.pr_scan_id, unblock=False)
                logger.info("PR scan %s blocked (whitelist is inactive).", vuln.pr_scan_id)

    # ------------------------------------------------------
    # 6) Commit and return
    # ------------------------------------------------------
    await db.commit()
    logger.info("Vulnerabilities and related incidents updated for whitelist_id=%s.", whitelist_id)

    return result.rowcount if result.rowcount is not None else 0