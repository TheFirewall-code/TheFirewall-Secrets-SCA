from app.modules.incidents.schemas.activity_schemas import ActivityCreate
from app.modules.incidents.services.activity_service import add_activity
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from app.modules.incidents.models.incident_model import Incidents, IncidentClosedBy
from app.modules.incidents.schemas.incident_schemas import IncidentBase, IncidentUpdate, IncidentStatusEnum, IncidentTypeEnum, IncidentResponse, IncidentFilters, BulkIncidentUpdate
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from app.utils.pagination import paginate
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, extract, func
from app.modules.user.models.user import User
from app.modules.incidents.models.activity_model import Action
from app.modules.secrets.model.secrets_model import Secrets, SeverityLevel, ScanType
from sqlalchemy import func, distinct
from app.modules.repository.models.repository import Repo
from sqlalchemy import select, func, literal_column, update, distinct, cast, String, or_
from app.modules.groups.models.group_model import Group
from typing import Dict
from app.modules.pr.models.pr import PR
from sqlalchemy import asc, desc

def convert_datetime_format(date_string):
    if date_string:
        parsed_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
        return parsed_date.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return None


# Create a new incident and add a corresponding activity
async def create_incident(db: AsyncSession, incident: IncidentBase):
    # Create a new incident
    new_incident = Incidents(
        name=incident.name,
        type=incident.type,
        status=incident.status,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        secret_id=incident.secret_id,
        vulnerability_id=incident.vulnerability_id,
    )
    db.add(new_incident)
    await db.commit()
    await db.refresh(new_incident)

    # Create an activity for the new incident
    activity_data = ActivityCreate(
        incident_id=new_incident.id,
        action=Action.INCIDENT_OPENED,
        new_value=incident.status
    )
    await add_activity(db=db, activity_data=activity_data)

    return new_incident


async def count_incidents_by_severity(
        db: AsyncSession,
        incident_type: Optional[IncidentTypeEnum]
) -> List[Dict[str, str]]:
    # Define severity levels and their labels
    severity_labels = {
        SeverityLevel.LOW: "Low",
        SeverityLevel.MEDIUM: "Medium",
        SeverityLevel.HIGH: "High",
        SeverityLevel.CRITICAL: "Critical"
    }

    # Define the statuses to filter on
    statuses = [IncidentStatusEnum.OPEN, IncidentStatusEnum.IN_PROGRESS]

    if incident_type == IncidentTypeEnum.secret:
        # Query for secret incidents using the Secrets table (severity is an enum)
        query = (
            select(Secrets.severity, func.count(Secrets.id))
            .join(Incidents, Secrets.id == Incidents.secret_id)
            .where(
                Incidents.type == incident_type,
                Incidents.status.in_(statuses)
            )
            .group_by(Secrets.severity)
        )
        result = await db.execute(query)
        # The result is already keyed by a SeverityLevel enum.
        severity_counts = dict(result.all())

    elif incident_type == IncidentTypeEnum.vulnerability:
        # Query for vulnerability incidents using the Vulnerability table (severity stored as string)
        query = (
            select(Vulnerability.severity, func.count(Vulnerability.id))
            .join(Incidents, Vulnerability.id == Incidents.vulnerability_id)
            .where(
                Incidents.type == incident_type,
                Incidents.status.in_(statuses)
            )
            .group_by(Vulnerability.severity)
        )
        result = await db.execute(query)
        raw_counts = result.all()
        severity_counts = {}
        # Convert the returned string to a SeverityLevel enum.
        for sev_str, count in raw_counts:
            try:
                # Normalize the string for conversion (if stored in lower-case, adjust accordingly)
                sev_enum = SeverityLevel(sev_str.lower())
                severity_counts[sev_enum] = count
            except ValueError:
                # If conversion fails, skip or handle as desired.
                continue
    else:
        # Optionally, handle the case where incident_type is not provided.
        return []

    # Build the response using the predefined severity_labels.
    response = [
        {
            "label": severity_labels.get(severity, "Unknown"),
            "value": severity.name,  # use the enum's name (e.g. "LOW", "MEDIUM", etc.)
            "count": severity_counts.get(severity, 0)  # default count to 0 if not present
        }
        for severity in SeverityLevel
        if severity in severity_labels  # include only the desired severities
    ]

    return response


async def get_incidents(
    db: AsyncSession,
    filters: IncidentFilters,
    incident_type: IncidentTypeEnum,
    page: int = 1,
    limit: int = 10,
    repo_ids: Optional[List[int]] = None,
    vc_ids: Optional[List[int]] = None,
    pr_ids: Optional[List[int]] = None,
    group_ids: Optional[List[int]] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    sort_by: Optional[str] = "created_at",
    order_by: Optional[str] = "desc",
) -> dict:
    # Step 1: (Optional) Resolve repository IDs from group_ids if provided.
    if group_ids:
        group_repo_query = (
            select(Repo.id)
            .join(Group.repos)
            .where(Group.id.in_(group_ids))
        )
        group_repo_result = await db.execute(group_repo_query)
        group_repo_ids = [row[0] for row in group_repo_result.fetchall()]

        if repo_ids:
            repo_ids = list(set(repo_ids).intersection(group_repo_ids))
        else:
            repo_ids = group_repo_ids

        if group_ids and not repo_ids:
            return {
                "data": [],
                "current_page": 0,
                "total_pages": 0,
                "current_limit": 0,
                "total_count": 0,
            }

    # Step 2: Build base query with appropriate joins.
    if incident_type == IncidentTypeEnum.secret:
        # For secret incidents, join the Secrets table and its related repository and PR.
        query = (
            select(Incidents)
            .outerjoin(Secrets, Incidents.secret_id == Secrets.id)
            .outerjoin(Repo, Secrets.repository_id == Repo.id)
            .outerjoin(PR, Secrets.pr_id == PR.id)
            .options(
                selectinload(Incidents.secret).selectinload(Secrets.repository),
                selectinload(Incidents.secret).selectinload(Secrets.pr),
            )
            .where(Incidents.type == incident_type)
        )
    else:  # Assume vulnerability
        # For vulnerability incidents, join the Vulnerability table and its related repository.
        query = (
            select(Incidents)
            .outerjoin(Vulnerability, Incidents.vulnerability_id == Vulnerability.id)
            .outerjoin(Repo, Vulnerability.repository_id == Repo.id)
            .options(
                selectinload(Incidents.vulnerability).selectinload(Vulnerability.repository),
            )
            .where(Incidents.type == incident_type)
        )

    filters_to_apply = []

    # Incident-level date filters
    if filters.created_after:
        filters_to_apply.append(Incidents.created_at >= filters.created_after)
    if filters.created_before:
        filters_to_apply.append(Incidents.created_at <= filters.created_before)
    if filters.updated_after:
        filters_to_apply.append(Incidents.updated_at >= filters.updated_after)
    if filters.updated_before:
        filters_to_apply.append(Incidents.updated_at <= filters.updated_before)

    # Common multi-select filter: statuses (if provided)
    if filters.statuses:
        # Assuming Incident.status is stored as a string or enum value
        filters_to_apply.append(Incidents.status.in_(filters.statuses))

    # ---------------------------------
    # Secret‑specific filters
    # (applied if incident_type == IncidentTypeEnum.secret)
    # ---------------------------------
    if incident_type == IncidentTypeEnum.secret:
        if filters.secrets:
            filters_to_apply.append(Secrets.secret.in_(filters.secrets))
        if filters.rules:
            filters_to_apply.append(Secrets.rule.in_(filters.rules))
        if filters.commits:
            filters_to_apply.append(Secrets.commit.in_(filters.commits))
        if filters.authors:
            filters_to_apply.append(Secrets.author.in_(filters.authors))
        if filters.emails:
            filters_to_apply.append(Secrets.email.in_(filters.emails))
        if filters.descriptions:
            filters_to_apply.append(Secrets.description.in_(filters.descriptions))
        if filters.pr_scan_id:
            filters_to_apply.append(Secrets.pr_scan_id == filters.pr_scan_id)
        if filters.whitelisted is not None:
            filters_to_apply.append(Secrets.whitelisted == filters.whitelisted)
        if filters.severities:
            # Convert each supplied severity to uppercase so that it matches the enum values stored in the database.
            severity_values = [s.upper() for s in filters.severities]
            filters_to_apply.append(Secrets.severity.in_(severity_values))
        if filters.scan_types:
            filters_to_apply.append(Secrets.scan_type.in_(filters.scan_types))
        if filters.messages:
            filters_to_apply.append(Secrets.message.in_(filters.messages))
        if filters.branches:
            filters_to_apply.append(Secrets.branch.in_(filters.branches))
        # Global search (using ilike) across selected secret fields.
        if filters.search:
            filters_to_apply.append(
                or_(
                    Secrets.secret.ilike(f"%{filters.search}%"),
                    Secrets.rule.ilike(f"%{filters.search}%"),
                    Secrets.description.ilike(f"%{filters.search}%"),
                    Secrets.commit.ilike(f"%{filters.search}%"),
                    Secrets.author.ilike(f"%{filters.search}%"),
                    Secrets.email.ilike(f"%{filters.search}%"),
                )
            )

    # ---------------------------------
    # Vulnerability‑specific filters
    # (applied if incident_type == IncidentTypeEnum.vulnerability)
    # ---------------------------------
    if incident_type == IncidentTypeEnum.vulnerability:
        if filters.vulnerability_ids:
            filters_to_apply.append(Vulnerability.vulnerability_id.in_(filters.vulnerability_ids))
        if filters.cve_ids:
            filters_to_apply.append(Vulnerability.cve_id.in_(filters.cve_ids))
        if filters.packages:
            filters_to_apply.append(Vulnerability.package.in_(filters.packages))
        if filters.package_versions:
            filters_to_apply.append(Vulnerability.package_version.in_(filters.package_versions))
        if filters.fix_available is not None:
            filters_to_apply.append(Vulnerability.fix_available == filters.fix_available)
        if filters.artifact_types:
            filters_to_apply.append(Vulnerability.artifact_type.in_(filters.artifact_types))
        if filters.artifact_paths:
            filters_to_apply.append(Vulnerability.artifact_path.in_(filters.artifact_paths))
        if filters.vulnerability_types:
            filters_to_apply.append(Vulnerability.vulnerability_type.in_(filters.vulnerability_types))
        if filters.licenses:
            filters_to_apply.append(Vulnerability.license.in_(filters.licenses))
        # Global search (using ilike) across vulnerability fields.
        if filters.search:
            filters_to_apply.append(
                or_(
                    Vulnerability.vulnerability_id.ilike(f"%{filters.search}%"),
                    Vulnerability.description.ilike(f"%{filters.search}%"),
                    Vulnerability.package.ilike(f"%{filters.search}%"),
                    Vulnerability.cve_id.ilike(f"%{filters.search}%"),
                )
            )
        if filters.severities:
            filters_to_apply.append(Vulnerability.severity.in_(filters.severities))
        if filters.whitelisted:
            filters_to_apply.append(Vulnerability.whitelisted == filters.whitelisted)


    # ---------------------------------
    # Repository, VC, PR filters (common to both types)
    # ---------------------------------
    if repo_ids:
        if incident_type == IncidentTypeEnum.secret:
            filters_to_apply.append(Secrets.repository_id.in_(repo_ids))
        else:
            filters_to_apply.append(Vulnerability.repository_id.in_(repo_ids))
    if vc_ids:
        filters_to_apply.append(Repo.vc_id.in_(vc_ids))
    if pr_ids:
        if incident_type == IncidentTypeEnum.secret:
            filters_to_apply.append(Secrets.pr_id.in_(pr_ids))
        else:
            filters_to_apply.append(Vulnerability.pr_id.in_(pr_ids))

    # Additional date filters
    if from_date:
        filters_to_apply.append(Incidents.created_at >= from_date)
    if to_date:
        filters_to_apply.append(Incidents.created_at <= to_date)

    # Apply all filter conditions to the query.
    for condition in filters_to_apply:
        query = query.where(condition)

    # ---------------------------------
    # Sorting - use asc/desc for sort_by field
    # ---------------------------------
    sort_mapping = {
        "created_at": Incidents.created_at,
        "updated_at": Incidents.updated_at,
        "severity": Secrets.severity if incident_type == IncidentTypeEnum.secret else Vulnerability.severity,
    }
    sort_column = sort_mapping.get(sort_by, Incidents.created_at)
    query = query.order_by(desc(sort_column) if order_by == "desc" else asc(sort_column))

    # ---------------------------------
    # Pagination
    # ---------------------------------
    total_count = await db.scalar(select(func.count()).select_from(query.subquery()))
    offset = (page - 1) * limit
    paginated_query = query.limit(limit).offset(offset)
    result = await db.execute(paginated_query)
    incidents = result.scalars().all()

    # Build and return the response.
    response_data = [
        {
            "id": incident.id,
            "name": incident.name,
            "status": incident.status,
            "type": incident.type,
            "created_at": incident.created_at,
            "updated_at": incident.updated_at,
            "closed_by": incident.closed_by,
            "secret": incident.secret,           # secret data if any
            "vulnerability": incident.vulnerability,  # vulnerability data if any
            "repository": {
                "id": incident.secret.repository.id if incident.secret and incident.secret.repository else None,
                "name": incident.secret.repository.other_repo_details.get("name")
                if (incident.secret and incident.secret.repository and incident.secret.repository.other_repo_details)
                else None,
            } if incident.secret else None,
        }
        for incident in incidents
    ]

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        "data": response_data,
        "current_page": page,
        "current_limit": limit,
        "total_count": total_count,
        "total_pages": total_pages,
    }


async def get_filter_values(
    db: AsyncSession,
    filter_name: str,
    incident_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> dict:

    # Example mapping for plural keys to actual model column names.
    FILTER_COLUMN_MAP = {
        'statuses': 'status',
        "severities": "severity",
        # Vulnerability-specific filters
        "vulnerability_ids": "vulnerability_id",
        "cve_ids": "cve_id",
        "packages": "package",
        "package_versions": "package_version",
        "artifact_types": "artifact_type",
        "artifact_paths": "artifact_path",
        "licenses": "license",
        # Secret-specific filters
        "secrets": "secret",
        "rules": "rule",
        "commits": "commit",
        "authors": "author",
        "emails": "email",
        "descriptions": "description",
        "scan_types": "scan_type",
        "messages": "message",
    }
    filter_name = FILTER_COLUMN_MAP.get(filter_name, filter_name)
    if filter_name in ["status", "type"]:
        model = Incidents
    elif filter_name == "group_ids":
        # For groups, assume we use Repo -> Group join
        query = (
            select(Group)
            .select_from(Repo)
            .join(Group, Repo.groups)
            .where(Group.id.is_not(None))
        )
    else:
        model = Vulnerability if incident_type == "vulnerability" else Secrets


    if filter_name != "group_ids":
        column = getattr(model, filter_name, None)
        if not column:
            raise ValueError(f"Invalid filter name: {filter_name}")

        query = select(distinct(column)).where(column.isnot(None))

    # Apply search filter using ilike only (for free‑text search)
    if search:
        if filter_name in ["status"]:
            query = query.filter(cast(Incidents.status, String).ilike(f"%{search}%"))
        elif filter_name in ["severity"]:
            query = query.filter(cast(Secrets.severity, String).ilike(f"%{search}%"))
        elif filter_name == "scan_type":
            query = query.filter(cast(Secrets.scan_type, String).ilike(f"%{search}%"))
        elif filter_name == "group_ids":
            query = query.filter(Group.name.ilike(f"%{search}%"))
        else:
            query = query.filter(cast(getattr(model, filter_name), String).ilike(f"%{search}%"))

    # Total count for pagination.
    if filter_name == "group_ids":
        total_count_query = (
            select(func.count(distinct(Group.id)))
            .select_from(Repo)
            .join(Group, Repo.groups)
        )
        if search:
            total_count_query = total_count_query.filter(Group.name.ilike(f"%{search}%"))
    else:
        total_count_query = select(func.count(distinct(getattr(model, filter_name))))
        if search:
            total_count_query = total_count_query.filter(
                cast(getattr(model, filter_name), String).ilike(f"%{search}%")
            )

    total_count = (await db.execute(total_count_query)).scalar()

    # Pagination.
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    values_raw = result.fetchall()
    # Extract the first column value.
    values = [row[0] for row in values_raw]

    # Format results (if the value is an Enum, use its value; otherwise, use str).
    def extract_value(item):
        return item.value if hasattr(item, "value") else str(item)

    if filter_name == "group_ids":
        formatted_values = [{"label": group.name, "value": group.id} for group in values]
    else:
        formatted_values = [{"label": extract_value(val), "value": extract_value(val)} for val in values]

    return {"values": formatted_values, "total": total_count}



# Update the status of an incident and create an activity


async def update_incident_status(
        db: AsyncSession,
        incident_id: int,
        status: IncidentStatusEnum,
        current_user: User) -> IncidentResponse:
    query = select(Incidents).where(
        Incidents.id == incident_id).options(
        joinedload(
            Incidents.secret))
    result = await db.execute(query)
    incident = result.scalars().first()

    if not incident:
        return None

    incident.status = status
    incident.updated_at = datetime.utcnow()

    if status == IncidentStatusEnum.CLOSED:
        incident.closed_by = IncidentClosedBy.USER

    # Commit the changes to the database
    await db.commit()
    await db.refresh(incident)

    # Create an activity for the status update
    if (status.value == "in-progress"):
        activity_data = ActivityCreate(
            incident_id=incident.id,
            action=Action.INCIDENT_IN_PROGRESS,
            new_value=status.value
        )
    elif (status.value == "open"):
        activity_data = ActivityCreate(
            incident_id=incident.id,
            action=Action.INCIDENT_OPENED,
            new_value=status.value
        )
    else:
        activity_data = ActivityCreate(
            incident_id=incident.id,
            action=Action.INCIDENT_CLOSED,
            new_value=status.value
        )

    await add_activity(db=db, activity_data=activity_data, current_user=current_user)

    return True

# Update the status of an incident and create an activity


async def update_incident_severity(
    db: AsyncSession,
    incident_id: int,
    severity: SeverityLevel,
    current_user: User
) -> IncidentResponse:
    # 1. Fetch the incident
    query = select(Incidents).where(Incidents.id == incident_id)
    result = await db.execute(query)
    incident = result.scalars().first()

    if not incident:
        return None

    print('Incident severity update', incident.vulnerability_id, incident.type)

    if incident.type.value == IncidentTypeEnum.vulnerability.value:
        vuln = (
            await db.execute(select(Vulnerability).where(Vulnerability.id == incident.vulnerability_id))
        ).scalar_one_or_none()

        if not vuln:
            return None

        old_severity = vuln.severity
        vuln.severity = severity.value
        vuln.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(vuln)

        activity_data = ActivityCreate(
            incident_id=incident.id,
            action=Action.SEVERITY_UPDATED,
            old_value=old_severity if old_severity else None,
            new_value=severity.value
        )
        await add_activity(db=db, activity_data=activity_data, current_user=current_user)
    else:
        secret = (
            await db.execute(
                select(Secrets).where(Secrets.id == incident.secret_id)
            )
        ).scalar_one_or_none()

        if not secret:
            return None

        old_severity = secret.severity
        secret.severity = severity
        secret.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(secret)

        activity_data = ActivityCreate(
            incident_id=incident.id,
            action=Action.SEVERITY_UPDATED,
            old_value=old_severity.value if old_severity else None,
            new_value=severity.value
        )
        await add_activity(db=db, activity_data=activity_data, current_user=current_user)

    return True
async def get_incident_by_id(db, incident_id: int) -> IncidentResponse:
    # Query the incident by its ID
    query = select(Incidents).where(
        Incidents.id == incident_id).options(
        joinedload(Incidents.secret), joinedload(Incidents.vulnerability))
    result = await db.execute(query)
    incident = result.scalars().first()

    return incident


async def get_trend(
    db: AsyncSession,
    interval: str = "monthly",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    status: Optional[IncidentStatusEnum] = None,
    incident_type: Optional[IncidentTypeEnum] = None,
):
    # If 'to_date' is not set, use current time
    if not to_date:
        to_date = datetime.utcnow()

    # If 'from_date' is not provided, use a default based on interval
    if not from_date:
        if interval == "daily":
            from_date = to_date - timedelta(days=1)
        elif interval == "weekly":
            from_date = to_date - timedelta(weeks=1)
        elif interval == "monthly":
            from_date = to_date - timedelta(days=30)
        else:
            return {"error": "Invalid interval. Use 'daily', 'weekly', or 'monthly'."}

    # Decide which table to join
    if incident_type == IncidentTypeEnum.vulnerability:
        join_table = Vulnerability
        join_condition = (Incidents.vulnerability_id == Vulnerability.id)
        repo_id_col = Vulnerability.repository_id
    else:
        # Default to Secrets
        join_table = Secrets
        join_condition = (Incidents.secret_id == Secrets.id)
        repo_id_col = Secrets.repository_id

    # Base query components
    group_by = Incidents.updated_at
    count_incidents = func.count(Incidents.id).label("incident_count")
    distinct_repos = func.count(func.distinct(repo_id_col)).label("repo_count")

    # Build query per interval
    if interval == "daily":
        query = (
            select(
                func.date(group_by).label("date"),
                count_incidents,
                distinct_repos
            )
            .join(join_table, join_condition)
            .where(group_by >= from_date, group_by <= to_date)
            .group_by(func.date(group_by))
        )
    elif interval == "weekly":
        query = (
            select(
                extract("year", group_by).label("year"),
                extract("week", group_by).label("week"),
                count_incidents,
                distinct_repos
            )
            .join(join_table, join_condition)
            .where(group_by >= from_date, group_by <= to_date)
            .group_by(extract("year", group_by), extract("week", group_by))
        )
    elif interval == "monthly":
        query = (
            select(
                extract("year", group_by).label("year"),
                extract("month", group_by).label("month"),
                count_incidents,
                distinct_repos
            )
            .join(join_table, join_condition)
            .where(group_by >= from_date, group_by <= to_date)
            .group_by(extract("year", group_by), extract("month", group_by))
        )
    else:
        return {"error": "Invalid interval. Use 'daily', 'weekly', or 'monthly'."}

    # Apply optional filters
    if status:
        query = query.where(Incidents.status == status)
    if incident_type:
        query = query.where(Incidents.type == incident_type)

    # Execute query
    rows = (await db.execute(query)).all()

    # Build response data
    if interval == "daily":
        incident_data = [
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "incident_count": row.incident_count,
                "repo_count": row.repo_count
            }
            for row in rows
        ]
    elif interval == "weekly":
        incident_data = [
            {
                "date": f"{int(row.year)}-W{int(row.week)}",
                "incident_count": row.incident_count,
                "repo_count": row.repo_count
            }
            for row in rows
        ]
    else:  # monthly
        incident_data = [
            {
                "date": f"{int(row.year)}-{int(row.month):02d}",
                "incident_count": row.incident_count,
                "repo_count": row.repo_count
            }
            for row in rows
        ]

    return {
        "interval": interval,
        "incident_data": incident_data,
        "from_date": from_date,
        "to_date": to_date
    }


async def get_severity_breakdown(
    db: AsyncSession,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    status: Optional[IncidentStatusEnum] = None,
    incident_type: Optional[IncidentTypeEnum] = None,
):
    # Default 'to_date' to now if not provided
    if not to_date:
        to_date = datetime.utcnow()

    # Default 'from_date' to 30 days prior if not provided
    if not from_date:
        from_date = to_date - timedelta(days=30)

    # Decide which table/column to use based on incident_type
    if incident_type == IncidentTypeEnum.vulnerability:
        join_table = Vulnerability
        join_condition = (Incidents.vulnerability_id == Vulnerability.id)
        severity_column = Vulnerability.severity
    else:
        # Default to Secrets
        join_table = Secrets
        join_condition = (Incidents.secret_id == Secrets.id)
        severity_column = Secrets.severity

    group_by = Incidents.updated_at

    # Build the query
    query = (
        select(
            severity_column,
            func.count(Incidents.id).label("incident_count")
        )
        .join(join_table, join_condition)
        .where(group_by >= from_date, group_by <= to_date)
        .group_by(severity_column)
    )

    # Apply optional status and incident_type filters
    if status:
        query = query.where(Incidents.status == status)
    if incident_type:
        query = query.where(Incidents.type == incident_type)

    # Execute the query
    rows = (await db.execute(query)).all()

    # Build the result
    severity_data = []
    for row in rows:
        severity = row[0]
        if isinstance(severity, str):
            severity_value = severity
        else:
            severity_value = severity.value

        severity_data.append({
            "value": severity_value,  # Use the extracted string value
            "label": severity_value.capitalize(),  # Capitalize for a human-readable label
            "count": row[1]
        })

    response_content = {
        "severity_breakdown": severity_data,
        "from_date": from_date,
        "to_date": to_date,
    }

    return response_content

async def get_incidents_top_repo(
    db: AsyncSession,
    severities: List[SeverityLevel],  # or strings
    repo_length: Optional[int] = 5,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    incident_type: Optional[IncidentTypeEnum] = None
):
    # Normalize time range
    now = datetime.utcnow()
    if to_date is None:
        to_date = now
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    # Decide which table/columns to join
    if incident_type == IncidentTypeEnum.vulnerability:
        join_table = Vulnerability
        join_condition = (Vulnerability.id == Incidents.vulnerability_id)
        severity_col = Vulnerability.severity
        repo_col = Vulnerability.repository_id
    else:
        join_table = Secrets
        join_condition = (Secrets.id == Incidents.secret_id)
        severity_col = Secrets.severity
        repo_col = Secrets.repository_id

    normalized_severities = [
        s.value.lower() if hasattr(s, 'value') else str(s).lower()
        for s in severities
    ]

    query = (
        select(
            Repo.id.label("repository_id"),
            Repo.name.label("repository_name"),
            Repo.author.label("repository_author"),
            func.count(Incidents.id).label("incident_count")
        )
        .join(join_table, join_condition)
        .join(Repo, repo_col == Repo.id)
        .where(
            Incidents.created_at >= from_date,
            Incidents.created_at <= to_date,
            func.lower(cast(severity_col, String)).in_(normalized_severities)
        )
        .group_by(Repo.id)
        .order_by(desc(func.count(Incidents.id)))
        .limit(repo_length)
    )

    if incident_type:
        query = query.where(Incidents.type == incident_type)

    result = await db.execute(query)
    repos = result.all()

    # Build the response
    repo_data = [
        {
            "repository_id": row.repository_id,
            "repository_name": row.repository_name,
            "repository_author": row.repository_author,
            "incident_count": row.incident_count
        }
        for row in repos
    ]

    return {
        "severities": severities,
        "repository_data": repo_data,
        "from_date": from_date,
        "to_date": to_date
    }


from sqlalchemy import cast, String, func

async def get_repo_count_by_severity(
    db: AsyncSession,
    severities: List[SeverityLevel],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    incident_type: Optional[IncidentTypeEnum] = None
):
    current_time = datetime.utcnow()

    if to_date is None:
        to_date = current_time

    if from_date is None:
        from_date = to_date - timedelta(days=30)

    normalized_severities = [
        s.value.lower() if hasattr(s, "value") else str(s).lower()
        for s in severities
    ]

    # Decide which table to join (Secrets vs. Vulnerabilities)
    if incident_type == IncidentTypeEnum.vulnerability:
        join_table = Vulnerability
        join_condition = (Incidents.vulnerability_id == Vulnerability.id)
        severity_col = Vulnerability.severity
        repo_id_col = Vulnerability.repository_id
    else:
        join_table = Secrets
        join_condition = (Incidents.secret_id == Secrets.id)
        severity_col = Secrets.severity
        repo_id_col = Secrets.repository_id

    # Build the query
    query = (
        select(
            severity_col.label("severity"),
            func.count(func.distinct(Repo.id)).label("repo_count"),
        )
        .join(Incidents, join_condition)
        .join(Repo, repo_id_col == Repo.id)
        .where(
            Incidents.created_at >= from_date,
            Incidents.created_at <= to_date,
            # Cast the severity to String, then apply lower() for case-insensitive matching
            func.lower(cast(severity_col, String)).in_(normalized_severities),
        )
        .group_by(severity_col)
    )

    if incident_type:
        query = query.where(Incidents.type == incident_type)

    result = await db.execute(query)
    severity_repo_counts = result.all()

    repo_data_by_severity = []
    for row in severity_repo_counts:
        severity_value = row[0].value if hasattr(row[0], "value") else str(row[0])
        repo_data_by_severity.append(
            {
                "severity": severity_value,
                "repo_count": row[1],
            }
        )

    return {
        "severities": severities,
        "repo_data_by_severity": repo_data_by_severity,
        "from_date": from_date,
        "to_date": to_date
    }



async def bulk_update_incidents_by_ids(
    db: AsyncSession,
    incident_ids: List[int],
    update_data: BulkIncidentUpdate,
    current_user: User
) -> bool:
    query = select(Incidents).where(Incidents.id.in_(incident_ids))
    result = await db.execute(query)
    incidents = result.scalars().all()

    if not incidents:
        return True

    for incident in incidents:
        await update_incident_status(db, incident.id, update_data.status, current_user)

    await db.commit()
    return True


async def bulk_update_incidents_by_filters(
    db: AsyncSession,
    filters: IncidentFilters,
    update_data: BulkIncidentUpdate,
    current_user: User
) -> bool:
    page = 1  # Start with the first page
    batch_size = 1000  # Set the batch size to 1000

    # Loop until there are no more incidents to update
    while True:
        # Get a batch of incidents with the current page
        incidents_data = await get_incidents(db=db, filters=filters, page=page, limit=batch_size)
        incidents = incidents_data["data"]

        # If no incidents are found, exit the loop
        if not incidents:
            break

        # Update each incident in the current batch
        for incident in incidents:
            await update_incident_status(db, incident["id"], update_data.status, current_user)

        # Move to the next page
        page += 1

    return True
