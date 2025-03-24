from datetime import datetime
from app.core.db import get_db
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.modules.incidents.models.incident_model import Incidents
from app.modules.incidents.models.comment_model import Comments
from app.modules.incidents.models.activity_model import Activity
from app.modules.incidents.schemas.incident_schemas import IncidentBase, IncidentResponse, IncidentStatusEnum, IncidentTypeEnum, IncidentUpdate, IncidentFilters, BulkIncidentUpdateByIds, BulkIncidentUpdate, BulkIncidentUpdateByFilters, IncidentFetchParams
from app.modules.incidents.schemas.activity_schemas import ActivityResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole
from app.modules.incidents.schemas.comment_schemas import CommentBase, CommentResponse
from typing import Dict
from app.modules.secrets.model.secrets_model import SeverityLevel
from datetime import datetime, timezone

from app.modules.incidents.services.incident_service import (
    get_incidents,
    get_incident_by_id,
    update_incident_status,
    get_filter_values,
    get_trend,
    get_severity_breakdown,
    get_incidents_top_repo,
    get_repo_count_by_severity,
    update_incident_severity,
    bulk_update_incidents_by_ids,
    bulk_update_incidents_by_filters,
    count_incidents_by_severity
)

from app.modules.incidents.services.activity_service import get_activities

from app.modules.incidents.services.comment_service import (
    create_comment,
    get_comments_by_incident_id
)
from app.modules.incidents.models.incident_model import IncidentStatusEnum
from pydantic import BaseModel



router = APIRouter(
    prefix="/incident",
    tags=["incidents"]
)

@router.post(
    "/",
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))],
)
async def fetch_incidents(
        params: IncidentFetchParams = Body(..., description="Incident fetch parameters"),
        db: AsyncSession = Depends(get_db),
):
    return await get_incidents(
        db=db,
        filters=params,
        incident_type=params.incident_type,
        page=params.page,
        limit=params.limit,
        repo_ids=params.repo_ids,
        vc_ids=params.vc_ids,
        pr_ids=params.pr_ids,
        group_ids=params.group_ids,
        from_date=params.from_date,
        to_date=params.to_date,
        sort_by=params.sort_by,
        order_by=params.order_by,
    )


# List available filter fields
@router.get(
    "/filters",
    dependencies=[Depends(role_required([
        UserRole.admin,
        UserRole.user,
        UserRole.readonly
    ]))]
)
async def list_available_filters(
    type: Optional[IncidentTypeEnum] = Query(None, alias="type")
):
    """
    Return a list of available filters.
    If 'type' is provided, return only the relevant filters for that type;
    otherwise, return all filters.
    """

    # Common filters (apply to both secret & vulnerability)
    common_filters = [
        {"key": "type", "label": "Type", "type": "text", "searchable": True},
        {"key": "statuses", "label": "Type", "type": "text", "searchable": True},
        {"key": "repo_ids", "label": "Repositories", "type": "api", "searchable": True},
        {"key": "vc_ids", "label": "Version Control Systems", "type": "api", "searchable": True},
        {"key": "pr_ids", "label": "Pull Requests", "type": "api", "searchable": True},
        {"key": "group_ids", "label": "Groups", "type": "api", "searchable": True},
        {"key": "severities", "label": "Severity", "type": "text", "searchable": True},
        {"key": "created_at", "label": "Created At", "type": "datetime", "searchable": True},
        {"key": "created_after", "label": "Created After", "type": "datetime", "searchable": True},
        {"key": "created_before", "label": "Created Before", "type": "datetime", "searchable": True},
        {"key": "updated_after", "label": "Updated After", "type": "datetime", "searchable": True},
        {"key": "updated_before", "label": "Updated Before", "type": "datetime", "searchable": True},
    ]

    # Secret-specific filters (updated for multi-select)
    secret_filters = [
        {"key": "secrets", "label": "Secrets", "type": "multi-select", "searchable": True},
        {"key": "rules", "label": "Rules", "type": "multi-select", "searchable": True},
        {"key": "commits", "label": "Commits", "type": "multi-select", "searchable": True},
        {"key": "authors", "label": "Authors", "type": "multi-select", "searchable": True},
        {"key": "emails", "label": "Emails", "type": "multi-select", "searchable": True},
        {"key": "descriptions", "label": "Descriptions", "type": "multi-select", "searchable": True},
        {"key": "whitelisted", "label": "Allowlist", "type": "boolean", "searchable": True},
        {"key": "pr_scan_id", "label": "PR Scan ID", "type": "number", "searchable": True},
        {"key": "scan_types", "label": "Scan Types", "type": "multi-select", "searchable": True},
        {"key": "messages", "label": "Commit Messages", "type": "multi-select", "searchable": True},
    ]

    # Vulnerability-specific filters (updated for multi-select)
    vulnerability_filters = [
        {"key": "vulnerability_ids", "label": "Vulnerability IDs", "type": "multi-select", "searchable": True},
        {"key": "cve_ids", "label": "CVE IDs", "type": "multi-select", "searchable": True},
        {"key": "packages", "label": "Packages", "type": "multi-select", "searchable": True},
        {"key": "package_versions", "label": "Package Versions", "type": "multi-select", "searchable": True},
        {"key": "fix_available", "label": "Fix Available", "type": "boolean", "searchable": True},
        {"key": "artifact_types", "label": "Artifact Types", "type": "multi-select", "searchable": True},
        {"key": "artifact_paths", "label": "Artifact Paths", "type": "multi-select", "searchable": True},
        {"key": "vulnerability_types", "label": "Vulnerability Type", "type": "text", "searchable": True},
        {"key": "licenses", "label": "Licenses", "type": "multi-select", "searchable": True},
        {"key": "whitelisted", "label": "Allowlist", "type": "boolean", "searchable": True},
    ]

    # Decide which filters to return based on 'incident_type'
    if type == IncidentTypeEnum.secret:
        # Return only common + secret-specific
        all_filters = common_filters + secret_filters
    elif type == IncidentTypeEnum.vulnerability:
        # Return only common + vulnerability-specific
        all_filters = common_filters + vulnerability_filters
    else:
        # Return all filters if 'type' is not provided
        all_filters = common_filters + secret_filters + vulnerability_filters

    return {"filters": all_filters}

# Get distinct filter values for a specific field
@router.get("/filters/{filter_name}/values",
            dependencies=[Depends(role_required([
                UserRole.admin,
                UserRole.user,
                UserRole.readonly
            ]))])
async def get_filter_values_endpoint(
    filter_name: str,
    type: Optional[IncidentTypeEnum] = Query(None, alias="type"),
    search: Optional[str] = Query(None, description="Search within the filter values"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Return distinct filter values for a given filter name.
    If `incident_type` is provided, the query is run against either
    Secrets or Vulnerabilities (or some other logic).
    """
    return await get_filter_values(
        db=db,
        filter_name=filter_name,
        incident_type=type.value,
        search=search,
        page=page,
        page_size=page_size
    )


# Get all activities for a specific incident
@router.get("/{incident_id}/activities")
async def get_all_activities(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 10,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    sort_by: Optional[str] = "created_at", 
    order_by: Optional[str] = "desc",
):
    """
    Get all activities for a specific incident with optional filters and sorting.
    """
    try:
        # Fetch paginated activities with sorting
        activities_data = await get_activities(
            db=db,
            incident_id=incident_id,
            page=page,
            page_size=page_size,
            action=action,
            user_id=user_id,
            old_value=old_value,
            new_value=new_value,
            sort_by=sort_by,
            order_by=order_by,
        )
        return activities_data

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# add a comment to an incident
@router.post('/comments',
             response_model=CommentResponse,
             dependencies=[Depends(role_required([UserRole.admin,
                                                  UserRole.user,
                                                  UserRole.readonly]))])
async def add_comment(
    db: Session = Depends(get_db),
    comment: CommentBase = None,
    current_user=Depends(get_current_user)
):
    comment = await create_comment(db=db, comment=comment, current_user=current_user)
    return comment


@router.get('/{incident_id}/comments',
            response_model=Dict,
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def get_comments(
    incident_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1)
) -> Dict:
    results = await get_comments_by_incident_id(db, incident_id, page, limit)
    return results

# Endpoint to update the incident status


@router.patch('/{incident_id}/status',
              dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def update_status(
    incident_id: int,
    status: IncidentStatusEnum,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    incident = await update_incident_status(db, incident_id, status, current_user)

    if not incident:
        raise HTTPException(status_code=404,
                            detail="Incident not found or update failed")

    return incident


# Endpoint to update the incident status
@router.patch('/{incident_id}/severity',
              dependencies=[Depends(role_required([UserRole.admin, UserRole.user]))])
async def update_status(
    incident_id: int,
    severity: SeverityLevel,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    incident = await update_incident_severity(db, incident_id, severity, current_user)

    if not incident:
        raise HTTPException(status_code=404,
                            detail="Incident not found or update failed")

    return incident

@router.get("/severity-count", dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))])
async def fetch_incident_severity_counts(
    db: AsyncSession = Depends(get_db),
    incident_type: Optional[IncidentTypeEnum] = Query(IncidentTypeEnum.secret, description="Type of incident to filter by")
):

    return await count_incidents_by_severity(db=db, incident_type=incident_type)
    
# Endpoint to fetch incident by its incident_id
@router.get('/{incident_id}',
            dependencies=[Depends(role_required([UserRole.admin,
                                                 UserRole.user,
                                                 UserRole.readonly]))])
async def fetch_incident_by_id(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Fetch the incident by ID using the service function
    incident = await get_incident_by_id(db, incident_id)

    # If the incident is not found, raise a 404 error
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


# Line Chart: Incident Trends
@router.get(
    '/dashboard/incidents/trend',
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))],
    summary="Retrieve incident trends",
    description="Fetch trends in incidents grouped by daily, weekly, or monthly intervals."
)
async def get_trends(
    db: AsyncSession = Depends(get_db),
    interval: str = Query("monthly", description="Interval type: 'daily', 'weekly', 'monthly'"),
    from_date: Optional[datetime] = Query(None, description="Start date in YYYY-MM-DD format"),
    to_date: Optional[datetime] = Query(None, description="End date in YYYY-MM-DD format"),
    status: Optional[IncidentStatusEnum] = Query(None, description="Filter by incident status"),
    incident_type: Optional[IncidentTypeEnum] = Query(None, description="SECRET or VULNERABILITY")
):
    return await get_trend(db, interval, from_date, to_date, status=status, incident_type=incident_type)


# Pie Chart: Severity Split
@router.get(
    '/dashboard/incidents/severity_split',
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))],
    summary="Retrieve incident severity split",
    description="Fetch the distribution of incidents across different severity levels."
)
async def get_severity(
    db: AsyncSession = Depends(get_db),
    from_date: Optional[datetime] = Query(None, description="Start date in YYYY-MM-DDTHH:MM:SS format"),
    to_date: Optional[datetime] = Query(None, description="End date in YYYY-MM-DDTHH:MM:SS format"),
    status: Optional[IncidentStatusEnum] = Query(None, description="Filter by incident status"),
    incident_type: Optional[IncidentTypeEnum] = Query(None, description="SECRET or VULNERABILITY")
):
    return await get_severity_breakdown(db, from_date, to_date, status=status, incident_type=incident_type)


# List: Top Repositories with Incidents
@router.get(
    '/dashboard/incidents/top-repos',
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))],
    summary="Retrieve top repositories",
    description="Fetch the top repositories based on the number of incidents and severity."
)
async def get_top_repos(
    db: AsyncSession = Depends(get_db),
    severities: List[SeverityLevel] = Query(["high", "critical", "low", "medium", "unknown"], description="List of severity levels to filter"),
    repo_length: Optional[int] = Query(5, description="Number of top repositories to retrieve"),
    from_date: Optional[datetime] = Query(None, description="Start date in YYYY-MM-DD format"),
    to_date: Optional[datetime] = Query(None, description="End date in YYYY-MM-DD format"),
    incident_type: Optional[IncidentTypeEnum] = Query(None, description="SECRET or VULNERABILITY")
):
    return await get_incidents_top_repo(db=db, from_date=from_date, to_date=to_date, severities=severities, repo_length=repo_length, incident_type=incident_type)


# Repository Split: Count by Severity
@router.get(
    '/dashboard/incidents/repo-split',
    dependencies=[Depends(role_required([UserRole.admin, UserRole.user, UserRole.readonly]))],
    summary="Retrieve repository severity split",
    description="Fetch the count of repositories grouped by severity levels."
)
async def get_repo_count_by_severity_con(
    db: AsyncSession = Depends(get_db),
    severities: List[SeverityLevel] = Query(["high", "critical", "low", "medium", "unknown"], description="List of severity levels to filter"),
    from_date: Optional[datetime] = Query(None, description="Start date in YYYY-MM-DD format"),
    to_date: Optional[datetime] = Query(None, description="End date in YYYY-MM-DD format"),
    incident_type: Optional[IncidentTypeEnum] = Query(None, description="SECRET or VULNERABILITY")
):
    return await get_repo_count_by_severity(db=db, from_date=from_date, to_date=to_date, severities=severities, incident_type=incident_type)



# In `incident_controller.py`

@router.patch('/bulk-update/by-ids',
              dependencies=[Depends(role_required([UserRole.admin,UserRole.user]))])
async def bulk_update_by_ids(
    update_data: BulkIncidentUpdateByIds,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await bulk_update_incidents_by_ids(
        db=db,
        incident_ids=update_data.incident_ids,
        update_data=update_data,
        current_user=current_user
    )
    if not result:
        raise HTTPException(status_code=404,
                            detail="Incidents not found or update failed")
    return {"detail": "Incidents updated successfully"}


@router.patch('/bulk-update/by-filters',
              dependencies=[Depends(role_required([UserRole.admin,UserRole.user]))])
async def bulk_update_by_filters(
    update_data: BulkIncidentUpdateByFilters,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await bulk_update_incidents_by_filters(
        db=db,
        filters=update_data.filters,
        update_data=update_data,
        current_user=current_user
    )
    if not result:
        raise HTTPException(status_code=404,
                            detail="Incidents not found or update failed")
    return {"detail": "Incidents updated successfully"}



