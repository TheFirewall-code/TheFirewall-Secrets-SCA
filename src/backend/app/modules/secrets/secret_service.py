from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, load_only
from app.modules.repository.models.repository import Repo
from sqlalchemy import select, func, literal_column, update, distinct, cast, String, or_
from app.modules.secrets.model.secrets_model import Secrets, SeverityLevel
from app.modules.secrets.schema.secret_schema import SecretsUpdate, GetSecretsRequest, SecretsResponse
from app.core.logger import logger
from datetime import datetime
from app.modules.repository.models.repository_scan import RepositoryScan
from fastapi import HTTPException, status
from app.utils.pagination import paginate
from app.modules.whitelist.whitelist_service import is_whitelisted

from app.modules.incidents.models.incident_model import IncidentStatusEnum, IncidentTypeEnum
from app.modules.incidents.schemas.incident_schemas import IncidentBase
from app.modules.incidents.services.incident_service import create_incident
from sqlalchemy import asc, desc
from math import ceil
from app.modules.whitelist.schema.whitelist_schema import WhiteListType


from datetime import datetime
from math import ceil


def make_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(
            datetime.now().astimezone().tzinfo).replace(
            tzinfo=None)
    return dt


async def add_secret(db: AsyncSession, secret_data: Secrets, scan=None) -> Secrets:
    existing_secret_query = select(Secrets).where(
        Secrets.secret == secret_data.secret,
        Secrets.fingerprint == secret_data.fingerprint,
        Secrets.file == secret_data.file,
        Secrets.line == secret_data.line,
        Secrets.repository_id == secret_data.repository_id,
        Secrets.live_commit_id == secret_data.live_commit_id,
        Secrets.pr_id == secret_data.pr_id
    )
    print("adding secret")
    result = await db.execute(existing_secret_query)
    existing_secret = result.scalars().first()

    whitelist_id = await is_whitelisted(db, WhiteListType.SECRET, secret_data.secret, secret_data.repository_id, secret_data.vc_id)

    if whitelist_id:
        secret_data.whitelist_id = whitelist_id
        secret_data.whitelisted = True

        await db.commit()

    if existing_secret:
        update_needed = False

        if existing_secret.pr_id is None and secret_data.pr_id:
            existing_secret.pr_id = secret_data.pr_id
            update_needed = True

        if existing_secret.pr_scan_id is None and secret_data.pr_scan_id:
            existing_secret.pr_scan_id = secret_data.pr_scan_id
            update_needed = True

        if existing_secret.live_commit_id is None and secret_data.live_commit_id:
            existing_secret.live_commit_id = secret_data.live_commit_id
            update_needed = True

        if existing_secret.live_commit_scan_id is None and secret_data.live_commit_scan_id:
            existing_secret.live_commit_scan_id = secret_data.live_commit_scan_id
            update_needed = True

        if existing_secret.repository_id is None and secret_data.repository_id:
            existing_secret.repository_id = secret_data.repository_id
            update_needed = True

        # Check if we need to update whitelisting information for the existing
        # secret
        if not existing_secret.whitelisted and secret_data.whitelisted:
            existing_secret.whitelist_id = secret_data.whitelist_id
            existing_secret.whitelisted = secret_data.whitelisted
            update_needed = True

        if update_needed:
            # Update the existing secret in the database
            await db.commit()

        # Return the existing secret
        print("Existing secret", existing_secret)
        return existing_secret

    # If no existing secret is found, create a new one
    db.add(secret_data)
    await db.commit()
    await db.refresh(secret_data)

    print("Created new secret", secret_data)

    incident = IncidentBase(
        name=secret_data.secret,
        type=IncidentTypeEnum.secret,
        status=IncidentStatusEnum.OPEN,
        secret_id=secret_data.id,
    )

    print("Creating incident", incident)
    await create_incident(db, incident)
    print("Created incident", incident)

    return secret_data


async def get_secret_by_id(db: AsyncSession, secret_id: int) -> Secrets:
    logger.info(f"Fetching secret with id: {secret_id}")
    result = await db.execute(select(Secrets).where(Secrets.id == secret_id).options(joinedload(Secrets.repository)))
    secret = result.scalar_one_or_none()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found")
    return secret


async def get_available_filters(db: AsyncSession) -> dict:
    logger.info("Request received to fetch available filters for secrets")
    filters = {
        "filters": [
            {"key": "secrets", "label": "Secrets", "type": "text", "searchable": True},
            {"key": "descriptions", "label": "Descriptions", "type": "text", "searchable": True},
            {"key": "repo_ids", "label": "Repositories", "type": "api", "searchable": True},
            {"key": "pr_ids", "label": "Pull Requests", "type": "api", "searchable": True},
            {"key": "vc_ids", "label": "VCs", "type": "api", "searchable": True},
            {"key": "severities", "label": "Severities", "type": "multi-select", "searchable": True},
            {"key": "scan_types", "label": "Scan Types", "type": "multi-select", "searchable": True},
            {"key": "rules", "label": "Rules", "type": "multi-select", "searchable": True},
            {"key": "commits", "label": "Commits", "type": "multi-select", "searchable": True},
            {"key": "authors", "label": "Authors", "type": "multi-select", "searchable": True},
            {"key": "messages", "label": "Commit Messages", "type": "multi-select", "searchable": True},
            {"key": "created_after", "label": "Created After", "type": "datetime", "searchable": True},
            {"key": "created_before", "label": "Created Before", "type": "datetime", "searchable": True},
        ]
    }
    return filters





async def update_secret(
        db: AsyncSession,
        secret_id: int,
        secret_update: SecretsUpdate) -> Secrets:
    logger.info(f"Updating secret with id: {secret_id}")

    stmt = (
        update(Secrets)
        .where(Secrets.id == secret_id)
        .values(**secret_update.dict(exclude_unset=True))
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()

    return await get_secret_by_id(db, secret_id)


async def delete_secret(db: AsyncSession, secret_id: int):
    logger.info(f"Deleting secret with id: {secret_id}")

    stmt = update(Secrets).where(Secrets.id == secret_id).values(deleted=True)
    await db.execute(stmt)
    await db.commit()

    return await get_secret_by_id(db, secret_id)


# Updated service to apply filters dynamically
async def get_secrets_by_param_service(
    db: AsyncSession,
    query: Optional[GetSecretsRequest] = None,
    search: Optional[str] = None,
    repo_ids: Optional[List[int]] = None,
    vc_ids: Optional[List[int]] = None,
    pr_ids: Optional[List[int]] = None,
    page: int = 1,
    limit: int = 10
):
    logger.info("Fetching secrets with search and filters")

    # Base query for secrets
    stmt = select(Secrets).options(
        joinedload(Secrets.repository).load_only(
            Repo.id,
            Repo.name,
            Repo.repoUrl,
            Repo.author,
            Repo.lastScanDate,
            Repo.created_at,
            Repo.other_repo_details
        )
    )

    # Fetch available filters dynamically
    available_filters = await get_available_filters(db)

    # Apply dynamic filtering based on the query
    if query:
        if query.pr_scan_id:
            stmt = stmt.where(Secrets.live_commit_scan_id == query.pr_scan_id)
        if query.commit_scan_id:
            stmt = stmt.where(Secrets.pr_scan_id == query.commit_scan_id)
        if query.secrets and any(f["key"] == "secrets" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.secret.in_(query.secrets))
        if query.severities and any(f["key"] == "severities" for f in available_filters["filters"]):
            severity_values = [s.upper() if isinstance(s, str) else s.value for s in query.severities]
            stmt = stmt.where(Secrets.severity.in_(severity_values))
        if query.whitelisted is not None and any(f["key"] == "whitelisted" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.whitelisted == query.whitelisted)
        if query.scan_types and any(f["key"] == "scan_types" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.scan_type.in_(query.scan_types))
        if query.authors and any(f["key"] == "authors" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.author.in_(query.authors))
        if query.emails and any(f["key"] == "emails" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.email.in_(query.emails))
        if query.rules and any(f["key"] == "rules" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.rule.in_(query.rules))
        if query.commits and any(f["key"] == "commits" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.commit.in_(query.commits))
        if query.messages and any(f["key"] == "messages" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.message.in_(query.messages))
        if query.branch and any(f["key"] == "branch" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.branches.in_(query.branch))

    # Filters for IDs
    if repo_ids and any(f["key"] == "repo_ids" for f in available_filters["filters"]):
        stmt = stmt.where(Secrets.repository_id.in_(repo_ids))
    if vc_ids and any(f["key"] == "vc_ids" for f in available_filters["filters"]):
        stmt = stmt.where(Secrets.vc_id.in_(vc_ids))
    if pr_ids and any(f["key"] == "pr_ids" for f in available_filters["filters"]):
        stmt = stmt.where(Secrets.pr_id.in_(pr_ids))

    # Apply global search
    if search:
        stmt = stmt.where(
            (Secrets.secret.ilike(f"%{search}%")) |
            (Secrets.rule.ilike(f"%{search}%")) |
            (Secrets.description.ilike(f"%{search}%")) |
            (Secrets.commit.ilike(f"%{search}%")) |
            (Secrets.author.ilike(f"%{search}%")) |
            (Secrets.email.ilike(f"%{search}%"))
        )

    # Count query for pagination
    count_query = select(func.count()).select_from(stmt.subquery())
    total_count = (await db.execute(count_query)).scalar()

    # Paginate the query results
    result_query = paginate(stmt, total_count, page, limit)
    result = await db.execute(result_query['query'])
    secrets = result.scalars().all()

    return {
        "data": secrets, **result_query['meta']
    }


async def get_distinct_secrets_with_repos(
    db: AsyncSession,
    query: Optional[GetSecretsRequest] = None,
    search: Optional[str] = None,
    repo_ids: Optional[List[int]] = None,
    vc_ids: Optional[List[int]] = None,
    pr_ids: Optional[List[int]] = None,
    page: int = 1,
    limit: int = 10
):
    """
    Fetch unique (secret + rule) rows, along with:
    - Number of distinct repositories (repo_count)
    - Average (normalized) score
    - Earliest creation time across matching secrets
    """

    # Start building the statement:
    # We'll group by secret+rule and do the necessary aggregates in one query.
    stmt = (
        select(
            Secrets.secret,
            Secrets.rule,
            func.count(distinct(Secrets.repository_id)).label("repo_count"),
            func.avg(Secrets.score_normalized).label("avg_score_normalized"),
            func.max(Secrets.created_at).label("created_at"),
        )
        .select_from(Secrets)
    )

    # We will apply all filters before grouping. Then we group by secret+rule.
    # (Applying filters first ensures that repo_count, min(created_at), etc.
    #  only reflect the filtered set of rows.)

    # Get the list of allowed filters from some helper function
    available_filters = await get_available_filters(db)

    # Apply dynamic filtering based on the query
    if query:
        if query.pr_scan_id:
            stmt = stmt.where(Secrets.live_commit_scan_id == query.pr_scan_id)
        if query.commit_scan_id:
            stmt = stmt.where(Secrets.pr_scan_id == query.commit_scan_id)
        if query.secrets and any(f["key"] == "secrets" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.secret.in_(query.secrets))
        if query.severities and any(f["key"] == "severities" for f in available_filters["filters"]):
            severity_values = []
            for s in query.severities:
                if isinstance(s, str):
                    severity_enum = SeverityLevel.__members__.get(s.upper())
                    if severity_enum:
                        severity_values.append(severity_enum)
                    else:
                        logger.warning(f"Invalid severity value provided: {s}")
                elif isinstance(s, SeverityLevel):
                    severity_values.append(s)
            if severity_values:
                stmt = stmt.where(Secrets.severity.in_(severity_values))
            stmt = stmt.where(Secrets.severity.in_(severity_values))
        if query.whitelisted is not None and any(f["key"] == "whitelisted" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.whitelisted == query.whitelisted)
        if query.scan_types and any(f["key"] == "scan_types" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.scan_type.in_(query.scan_types))
        if query.authors and any(f["key"] == "authors" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.author.in_(query.authors))
        if query.emails and any(f["key"] == "emails" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.email.in_(query.emails))
        if query.rules and any(f["key"] == "rules" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.rule.in_(query.rules))
        if query.commits and any(f["key"] == "commits" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.commit.in_(query.commits))
        if query.messages and any(f["key"] == "messages" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.message.in_(query.messages))
        if query.branch and any(f["key"] == "branch" for f in available_filters["filters"]):
            stmt = stmt.where(Secrets.branches.in_(query.branch))
        if query.created_after:
            stmt = stmt.where(Secrets.created_at >= query.created_after)
        if query.created_before:
            stmt = stmt.where(Secrets.created_at <= query.created_before)
        if query.descriptions:
            stmt = stmt.where(Secrets.description.in_(query.descriptions))

    # Filters for IDs
    if repo_ids and any(f["key"] == "repo_ids" for f in available_filters["filters"]):
        stmt = stmt.where(Secrets.repository_id.in_(repo_ids))
    if vc_ids and any(f["key"] == "vc_ids" for f in available_filters["filters"]):
        stmt = stmt.where(Secrets.vc_id.in_(vc_ids))
    if pr_ids and any(f["key"] == "pr_ids" for f in available_filters["filters"]):
        stmt = stmt.where(Secrets.pr_id.in_(pr_ids))

    # Apply global search
    if search:
        stmt = stmt.where(
            (Secrets.secret.ilike(f"%{search}%")) |
            (Secrets.rule.ilike(f"%{search}%")) |
            (Secrets.description.ilike(f"%{search}%")) |
            (Secrets.commit.ilike(f"%{search}%")) |
            (Secrets.author.ilike(f"%{search}%")) |
            (Secrets.email.ilike(f"%{search}%"))
        )

    # Now group by the (secret + rule) to get unique combinations
    stmt = stmt.group_by(Secrets.secret, Secrets.rule)

    # Sorting logic
    # We can't just reference the aggregated columns by their labels in order_by(...)
    # in most SQL dialects, so we handle them as python objects or use direct func calls.
    # Decide ascending or descending
    order_func = asc if (query and query.order_by == "asc") else desc

    if query and query.sort_by == "repo_count":
        # Sorting by COUNT(DISTINCT(...)) => replicate that expression here
        stmt = stmt.order_by(order_func(func.count(distinct(Secrets.repository_id))))
    elif query and query.sort_by == "created_at":
        stmt = stmt.order_by(order_func(func.min(Secrets.created_at)))
    elif query and query.sort_by == "score":
        stmt = stmt.order_by(order_func(func.avg(Secrets.score_normalized)))
    elif query and query.sort_by == "rule":
        # Sorting by Secrets.rule
        stmt = stmt.order_by(order_func(Secrets.rule))
    elif query and query.sort_by == "secret":
        # Sorting by Secrets.secret
        stmt = stmt.order_by(order_func(Secrets.secret))
    else:
        # Default sorting: descending by average score
        stmt = stmt.order_by(desc(func.avg(Secrets.score_normalized)))

    # 1) Get total count (number of unique rows after the GROUP BY).
    #    To do this in SQLAlchemy, we typically wrap the grouped statement
    #    in a subquery and count its rows:
    count_subq = stmt.with_only_columns(func.count()).subquery()
    total_count = (await db.execute(select(func.count()).select_from(count_subq))).scalar()

    # 2) Paginate
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    # 3) Execute
    result = await db.execute(stmt)
    rows = result.fetchall()

    # Transform results
    secrets_list = []
    for row in rows:
        secrets_list.append({
            "secret": row.secret,
            "rule": row.rule,
            "repo_count": row.repo_count,
            "avg_score_normalized": row.avg_score_normalized,
            "created_at": row.created_at,
        })

    total_pages = ceil(total_count / limit) if limit else 1

    logger.info(f"Fetched {len(secrets_list)} secrets with total count {total_count}.")

    return {
        "secrets": secrets_list,
        "total_count": total_count,
        "current_limit": limit,
        "current_page": page,
        "total_pages": total_pages,
    }

async def get_repos_for_secret(
    db: AsyncSession,
    secret_name: str,
    page: int = 1,
    limit: int = 10
):
    """
    Fetch unique repositories associated with a specific secret in paginated format,
    ensuring repositories are distinct by name.
    """
    # Query to fetch unique repository details for the given secret
    query_stmt = (
        select(
            Repo.id.label("repo_id"),
            Repo.name.label("repo_name"),
            Repo.repoUrl.label("repo_url"),
            Repo.author.label("author"),
            Repo.other_repo_details.label("other_repo_details")
        )
        .distinct(Repo.name)  # Ensure repositories are unique by name
        .join(Secrets, Secrets.repository_id == Repo.id)
        .where(Secrets.secret == secret_name)
        .order_by(Repo.name.asc())  # Order by repository name
    )

    # Count query for pagination
    count_query = select(func.count().label("total_count")).select_from(query_stmt.subquery())
    total_count = (await db.execute(count_query)).scalar()

    # Pagination logic
    offset = (page - 1) * limit
    query_stmt = query_stmt.offset(offset).limit(limit)

    # Execute the main query
    result = await db.execute(query_stmt)
    repos = result.fetchall()

    # Transform results into a list of dictionaries
    repos_list = [
        {
            "repo_id": row.repo_id,
            "repo_name": row.repo_name,
            "repo_url": row.repo_url,
            "author": row.author,
            "other_repo_details": row.other_repo_details
        }
        for row in repos
    ]

    total_pages = ceil(total_count / limit)

    logger.info(f"Fetched {len(repos_list)} unique repositories for secret '{secret_name}'.")

    return {
        "secret": secret_name,
        "repositories": repos_list,
        "total_count": total_count,
        "current_limit": limit,
        "current_page": page,
        "total_pages": total_pages,
    }


async def get_filter_values(
    db: AsyncSession,
    filter_name: str,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Dict[str, str]], int]:
    logger.info(f"Fetching distinct values for filter: {filter_name}, search={search}, page={page}, page_size={page_size}")

    if filter_name in ['sort_bys']:
        return ([{"label": value, "value": value} for value in ["repo_count", "secret", "rule"]], 3)
    if filter_name in ['order_bys']:
        return ([{"label": value, "value": value} for value in ["asc", "desc"]], 2)

    # Mapping plural UI keys to actual Secrets model column names.
    FILTER_COLUMN_MAP = {
        "secrets": "secret",
        "descriptions": "description",
        "severities": "severity",
        "scan_types": "scan_type",
        "rules": "rule",
        "commits": "commit",
        "authors": "author",
        "messages": "message",
        "created_ats": "created_at",
        "updated_ats": "updated_at",
    }

    actual_column_name = FILTER_COLUMN_MAP.get(filter_name, filter_name)
    if not hasattr(Secrets, actual_column_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filter name"
        )

    column = getattr(Secrets, actual_column_name)

    # Handle the case if the column represents an array (e.g., branches) if needed.
    if filter_name == "branches":
        query = select(func.unnest(column)).where(column.isnot(None))
    else:
        query = select(distinct(column)).where(column.isnot(None))

    # If filtering by a date field convert string to date.
    if filter_name in ["created_ats", "updated_ats"]:
        try:
            search_date = datetime.strptime(search, "%Y-%m-%d") if search else None
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD."
            )
        if search_date:
            query = query.where(func.date(column) == search_date)
    elif search:
        # For severity, if needed, convert search term to uppercase.
        if filter_name == "severities":
            query = query.where(cast(column, String).ilike(f"%{search.upper()}%"))
        elif filter_name == "scan_types":
            query = query.where(cast(column, String).ilike(f"%{search}%"))
        elif filter_name == "branches":
            query = query.where(func.array_to_string(column, ',').ilike(f"%{search}%"))
        else:
            query = query.where(cast(column, String).ilike(f"%{search}%"))

    total_count = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    paginated_query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(paginated_query)
    raw_values = [row[0] for row in result.fetchall()]

    if filter_name == "branches":
        raw_values = list(set(raw_values))

    if not raw_values:
        logger.warning(f"No values found for filter: {filter_name}, search: {search}")

    # Format values as list of { "label": value, "value": value }
    formatted_values = [{"label": str(value), "value": str(value)} for value in raw_values]

    return formatted_values, total_count