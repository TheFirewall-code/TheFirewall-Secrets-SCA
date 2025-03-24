from sqlalchemy import update, delete, desc, asc, or_, cast, String, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload, Query
from fastapi import HTTPException, status
from fastapi.exceptions import ResponseValidationError
from pydantic import ValidationError

from typing import List, Optional
from app.core.logger import logger
from datetime import datetime, timezone

from app.modules.secrets.model.secrets_model import Secrets, ScanType
from app.modules.repository.models.repository import Repo
from app.modules.repository.models.repository_scan import RepositoryScan, ScanStatusEnum
from app.modules.repository.schemas.repository_schema import RepoResponse, SecretsResponse, FilterOption
from app.modules.vc.models.vc import VC
from app.modules.vc.schemas.vc_schema import VCResponse
from app.modules.vc.vc_service import get_vc
from app.modules.user.models.user import User
from app.modules.repository.models.repository_scan import RepoScanType

from app.modules.secrets.secret_service import add_secret
from app.modules.slack_integration.slack_integration_service import fetch_and_notify_secrets

from app.utils.scan_repo_secrets import runScan
from app.utils.clone_repo import clone_repo, get_branches_from_commit
from app.utils.fetch_repos import fetch_repos
from app.utils.process_repo_data import process_repo_data
from app.utils.pagination import paginate
from app.utils.mark_severity import mark_severity
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from app.utils.sbom_generator import generate_sbom
from app.utils.delete_folder import delete_folder

from typing import List, Dict, Any
import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.future import select
import os


import time
# Scans all repositories for a given VC ID
import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Query
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Gets the repository by vc id
async def get_repos_by_vc_id(
    db: AsyncSession,
    vc_id: Optional[int] = None,
    vc_name: Optional[str] = None,
    repo_name: Optional[str] = None,
    sort_by: Optional[str] = None,
    order_by: Optional[str] = "asc",
    page: int = 1,
    limit: int = 10
) -> dict:
    try:
        query = select(Repo).options(
            selectinload(
                Repo.secrets), joinedload(
                Repo.vc))

        # if vc_name:
        #     vc_subquery = select(VC.id).where(VC.name.ilike(f"%{vc_name}%"))
        #     vc_result = await db.execute(vc_subquery)
        #     vc_id = vc_result.scalars().first()
        if vc_id:
            query = query.where(Repo.vc_id == vc_id)

        if repo_name:
            query = query.where(Repo.name == repo_name)

        order = asc if order_by == "asc" else desc
        if sort_by in [
                'lastScanDate',
                'created_at'] and hasattr(
                Repo,
                sort_by):
            query = query.order_by(order(getattr(Repo, sort_by)))
        elif sort_by == 'secrets_count':
            query = query.order_by(order(func.count(Repo.secrets)))

        total_count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await db.execute(total_count_query)
        total_count = total_count_result.scalar()

        pagination = paginate(query, total_count, page, limit)
        paginated_query = pagination['query']

        result = await db.execute(paginated_query)
        repos = result.scalars().all()

        repo_responses = [
            RepoResponse(
                id=repo.id,
                name=repo.name,
                repoUrl=repo.repoUrl,
                author=repo.author,
                other_repo_details=repo.other_repo_details,
                lastScanDate=repo.lastScanDate,
                created_at=repo.created_at,
                score_normalized=repo.score_normalized,
                score_normalized_on=repo.score_normalized_on,
                secrets_count=len(repo.secrets),
                vulnerability_count=0,
                vc=repo.vc,
                sca_branches=repo.sca_branches,
                secrets=[SecretsResponse.from_orm(secret) for secret in repo.secrets]
            )
            for repo in repos
        ]

        

        return {
            "data": repo_responses if repo_responses else [],
            **pagination['meta']
        }

    except ValidationError as ve:
        print(f"Validation Error: {ve.json()}")
        raise ResponseValidationError(ve.json())
    except Exception as e:
        print(f"Error in get_repos_by_vc_id: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



# Gets the repository by vc id
async def get_repos_for_vc_id(
    db: AsyncSession,
    vc_id: Optional[int] = None,
    page: int = 1,
    limit: int = 1_000_000
) -> dict:
    try:
        # Start the query
        query = select(Repo).options(
            selectinload(Repo.secrets), 
            joinedload(Repo.vc)
        )
        
        # Filter by vc_id
        if vc_id:
            query = query.where(Repo.vc_id == vc_id)
        
        # Calculate total count for pagination
        total_count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await db.execute(total_count_query)
        total_count = total_count_result.scalar()
        
        # Apply pagination
        pagination = paginate(query, total_count, page, limit)
        paginated_query = pagination['query']
        
        # Execute the query
        result = await db.execute(paginated_query)
        repos = result.scalars().all()
        
        # Format the response
        repo_responses = [
            RepoResponse(
                id=repo.id,
                name=repo.name,
                repoUrl=repo.repoUrl,
                author=repo.author,
                other_repo_details=repo.other_repo_details,
                lastScanDate=repo.lastScanDate,
                created_at=repo.created_at,
                score_normalized=repo.score_normalized,
                score_normalized_on=repo.score_normalized_on,
                secrets_count=len(repo.secrets),
                vulnerability_count=0,  # Defaulted to 0 if not provided
                vc=repo.vc,
                sca_branches=repo.sca_branches,
                secrets=[SecretsResponse.from_orm(secret) for secret in repo.secrets]
            )
            for repo in repos
        ]

        print("---------------------------------")
        print("repos length", len(repo_responses))
        print("---------------------------------")
        
        return {
            "data": repo_responses if repo_responses else [],
            **pagination['meta']
        }

        
    
    except ValidationError as ve:
        print(f"Validation Error: {ve.json()}")
        raise ResponseValidationError(ve.json())
    except Exception as e:
        print(f"Error in get_repos_for_vc_id: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



# fetches the repository when vc is added from the github, gitlab or bitbucket
async def fetch_all_repos_for_vc(
        db: AsyncSession,
        vc_id: int,
        current_user: User) -> None:
    try:
        vc = await get_vc(db, vc_id)

        repos_data = await fetch_repos(vc.url, vc.token, vc.type)

        for repo_data in repos_data:
            processed_repo_data = process_repo_data(repo_data, vc.type)

            existing_repo_result = await db.execute(
                select(Repo).filter(Repo.name == processed_repo_data['name'], Repo.vc_id == vc.id)
            )
            existing_repo = existing_repo_result.scalar_one_or_none()

            if existing_repo:
                await db.execute(
                    update(Repo)
                    .where(Repo.id == existing_repo.id)
                    .values(
                        lastScanDate=datetime.now(tz=timezone.utc).replace(tzinfo=None),
                        repoUrl=processed_repo_data['repoUrl'],
                        author=processed_repo_data['author'],
                        other_repo_details=processed_repo_data['other_repo_details']
                    )
                )
            else:
                new_repo = Repo(
                    vc_id=vc.id,
                    vctype=vc.type,
                    name=processed_repo_data['name'],
                    repoUrl=processed_repo_data['repoUrl'],
                    author=processed_repo_data['author'],
                    other_repo_details=processed_repo_data['other_repo_details'])
                db.add(new_repo)

        await db.commit()

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# scans an individual repository for secrets
async def scan_repo_by_id(
        db: AsyncSession,
        repository_id: int,
        current_user: Optional[User] = None) -> RepositoryScan:
    try:
        repo_result = await db.execute(select(Repo).filter(Repo.id == repository_id))
        repo = repo_result.scalar_one_or_none()

        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No repository found with ID {repository_id}"
            )

        vc_result = await db.execute(select(VC).filter(VC.id == repo.vc_id))
        vc = vc_result.scalar_one_or_none()

        if not vc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No VC found with ID {repo.vc_id}"
            )

        existing_scan_result = await db.execute(
            select(RepositoryScan)
            .filter(repository_id == RepositoryScan.repository_id,
                    RepoScanType.SECRET == RepositoryScan.scan_type,
                    RepositoryScan.status.in_([ScanStatusEnum.PENDING, ScanStatusEnum.IN_PROGRESS]))
            .limit(1)
        )
        existing_scan = existing_scan_result.scalar_one_or_none()

        if existing_scan:
            return existing_scan

        scan = RepositoryScan(
            repository_id=repo.id,
            created_at=datetime.utcnow(),
            status=ScanStatusEnum.PENDING,
            scan_type = RepoScanType.SECRET
        )
        db.add(scan)
        logger.info(f"Created Repo scan {scan}")

        try:
            await scan_repo(db, repo, vc.token, scan, vc.id)
        except Exception as e:
            logger.error(f"Error scanning repo: {str(e)}", exc_info=True)

        await db.commit()
        await db.refresh(scan)
        return scan

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(
            f"An error occurred while scanning repository {repository_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while scanning the repository"
        )




async def scan_all_repos_for_vc(
    db: AsyncSession,
    vc_id: int,
    current_user: Any
) -> List[Dict[str, Any]]:
    try:
        scan_count = 0
        print("Scanning all repos for VC", vc_id)

        # Query the VC by ID
        vc_query: Query = select(VC).where(VC.id == vc_id)
        result = await db.execute(vc_query)
        vc = result.scalars().one_or_none()

        if vc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version Control (VC) with ID {vc_id} not found"
            )

        if not vc.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version Control (VC) with ID {vc_id} is not active"
            )

        # Fetch repositories for the given VC ID
        repos_response = await get_repos_for_vc_id(db=db, vc_id=vc_id)
        repos = repos_response.get("data", [])

        print("Repos fetched for scanning", len(repos))

        if not repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No repositories found for VC ID {vc_id}"
            )

        # Perform scans on each repository
        scans = []
        for repo in repos:
            try:
                print("Sending repo for scanning", scan_count)
                # Create a task for scanning
                scan_task = asyncio.create_task(
                    scan_repo_by_id(db, repo.id, current_user)
                )
                # Add timeout using wait_for
                scan = await asyncio.wait_for(scan_task, timeout=15 * 60)  # 15 minutes
                scans.append(scan)
                print("Repos scanned", scan_count)
                scan_count += 1
            except asyncio.TimeoutError:
                logger.error(
                    f"Timeout occurred while scanning repository ID {repo.id}. Cancelling the scan."
                )
                scan_task.cancel()
                try:
                    await scan_task
                except asyncio.CancelledError:
                    logger.info(f"Scan for repository ID {repo.id} was successfully cancelled.")
            except Exception as scan_error:
                logger.error(
                    f"Error scanning repository ID {repo.id}: {scan_error}"
                )
                # Rollback the session to ensure it's valid for the next iteration
                await db.rollback()

        if not scans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No scans were successful for VC ID {vc_id}"
            )

        return scans

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(
            f"An error occurred while scanning repositories for VC ID {vc_id}: {str(e)}"
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while scanning repositories"
        )

# returns a repo by id
async def get_repo_by_id(
    db: AsyncSession,
    repo_id: int
) -> Repo:
    query: Query = select(Repo).where(Repo.id == repo_id)

    result = await db.execute(query)
    repo = result.scalars().one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No repositories found"
        )
    return repo


# scans a repo for secret
async def scan_repo(
        db: AsyncSession,
        repo: Repo,
        token: str,
        scan: RepositoryScan,
        vc_id: int,
        scan_count=0):
    try:
        scan.status = ScanStatusEnum.IN_PROGRESS
        await db.commit()
        repo_identifier = os.path.splitext(repo.repoUrl.rstrip('/').split('/')[-1])[0]

        target_dir = clone_repo(
            repo.vctype.value,
            repo.repoUrl,
            token,
            repo_identifier)
        
        secrets = runScan(target_dir, repo.name)
        print('Got secrets', secrets)

        if secrets and len(secrets) > 0:
            severity_count = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "informational": 0,
                "unknown": 0
            }

            for sec in secrets:
                if not isinstance(sec, dict) or "RuleID" not in sec:
                    print(f"Skipping secret: {sec}, missing 'RuleID'")
                    continue

                severity = mark_severity(sec.get("RuleID", "low"))
                severity_str = severity.value.lower() if isinstance(
                    severity, str) else str(severity.value).lower()

                secret_data = Secrets(
                    description=sec.get("Description"),
                    secret=sec.get("Secret"),
                    file=sec.get("File"),
                    symlink_file=sec.get("SymlinkFile", None),
                    line=f"{sec.get('StartLine', 0)}:{sec.get('EndLine', 0)}",
                    start_line=sec.get("StartLine", 0),
                    end_line=sec.get("EndLine", 0),
                    start_column=sec.get("StartColumn", 0),
                    end_column=sec.get("EndColumn", 0),
                    match=sec.get("Match"),
                    entropy=sec.get("Entropy"),
                    rule=sec.get("RuleID"),
                    fingerprint=sec.get("Fingerprint"),
                    message=sec.get("Message"),
                    commit=sec.get("Commit"),
                    author=sec.get("Author"),
                    email=sec.get("Email"),
                    severity=severity,
                    date=datetime.fromisoformat(sec.get("Date").replace("Z", "")),
                    tags=sec.get("Tags", []),
                    repository_id=repo.id,
                    scan_type=ScanType.REPO_SCAN,
                    vc_id=vc_id
                )

                print(secret_data)

                secret_data.branches = get_branches_from_commit(
                    target_dir, secret_data.commit)
                sec, new = await add_secret(db, secret_data, scan)
                if new and severity_str in severity_count:
                    severity_count[severity_str] += 1

            await fetch_and_notify_secrets(
                db=db,
                severity_count=severity_count,
                repo_name=repo.name,
                scan_type='Repository',
                repo_id=repo.id
            )

        delete_folder(target_dir)
        scan.status = ScanStatusEnum.COMPLETED
        await db.commit()


    except Exception as e:
        logger.error(
            f"An error occurred while processing repo {repo.name}: {str(e)}", exc_info=True)
        scan.status = ScanStatusEnum.FAILED

        if scan_count < 3:
            time.sleep(scan_count * 10)
            await scan_repo(db=db, repo=repo, token=token, scan=scan, vc_id=vc_id, scan_count=scan_count + 1)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An error occurred while processing repo {repo.name}: {str(e)}", exc_info=True)


# get all the repositories
async def get_repos(
    db: AsyncSession,
    repo_name: Optional[str] = None,
    vc_ids: Optional[List[int]] = None,
    repo_ids: Optional[List[int]] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    order_by: Optional[str] = "asc",
    page: int = 1,
    limit: int = 10,
    authors: Optional[List[str]] = None,
) -> dict:
    secret_count_subquery = (
        select(Repo.id, func.count(Secrets.id).label("secret_count"))
        .join(Secrets, Secrets.repository_id == Repo.id)
        .group_by(Repo.id)
        .subquery()
    )

    vulnerability_count_subquery = (
        select(Repo.id, func.count(Vulnerability.id).label("vulnerability_count"))
        .join(Vulnerability, Vulnerability.repository_id == Repo.id)
        .group_by(Repo.id)
        .subquery()
    )

    query = (
        select(Repo, secret_count_subquery.c.secret_count, vulnerability_count_subquery.c.vulnerability_count)
        .outerjoin(secret_count_subquery, Repo.id == secret_count_subquery.c.id)
        .outerjoin(vulnerability_count_subquery, Repo.id == vulnerability_count_subquery.c.id)
        .options(
            selectinload(Repo.secrets),
            selectinload(Repo.vc)
        )
    )

    if repo_name:
        query = query.where(Repo.name.ilike(f"%{repo_name}%"))

    if vc_ids:
        query = query.where(Repo.vc_id.in_(vc_ids))

    if repo_ids:
        query = query.where(Repo.id.in_(repo_ids))

    if created_after:
        query = query.where(func.date(Repo.created_at) >= created_after)
    if created_before:
        query = query.where(func.date(Repo.created_at) <= created_before)

    if search:
        search_query = f"%{search}%"
        query = query.where(
            or_(
                Repo.name.ilike(search_query),
                cast(Repo.vc_id, String).ilike(search_query),
                cast(Repo.id, String).ilike(search_query),
                func.to_char(Repo.created_at, 'YYYY-MM-DD').ilike(search_query)
            )
        )

    if authors:
        query = query.where(func.date(Repo.author).in_(authors))

    if sort_by:
        order = asc if order_by == "asc" else desc

        if sort_by == 'vc_id':
            query = query.order_by(order(Repo.vc_id))
        elif sort_by == 'score_normalized':
            query = query.order_by(order(Repo.score_normalized))
        elif sort_by == 'repo_id':
            query = query.order_by(order(Repo.id))
        elif sort_by == 'secrets_count':
            query = query.order_by(
                order(
                    func.coalesce(
                        secret_count_subquery.c.secret_count,
                        0)))
        elif sort_by == 'author':
            query = query.order_by(order(Repo.author))
        elif sort_by == 'vulnerability_count':
            query = query.order_by(
                order(
                    func.coalesce(
                        vulnerability_count_subquery.c.vulnerability_count,
                        0)))
        elif sort_by in ['lastScanDate', 'created_at']:
            query = query.order_by(order(getattr(Repo, sort_by)))

    total_count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar()

    pagination = paginate(query, total_count, page, limit)
    paginated_query = pagination['query']

    result = await db.execute(paginated_query)
    repo_results = result.all()

    repo_responses = [
        RepoResponse(
            id=repo[0].id,
            name=repo[0].name,
            repoUrl=repo[0].repoUrl,
            author=repo[0].author,
            other_repo_details=repo[0].other_repo_details,
            lastScanDate=repo[0].lastScanDate,
            created_at=repo[0].created_at,
            score_normalized=repo[0].score_normalized,
            score_normalized_on=repo[0].score_normalized_on,
            secrets_count=repo[1] if repo[1] is not None else 0,
            vulnerability_count=repo[2] if repo[2] is not None else 0,
            secrets=[SecretsResponse.from_orm(secret) for secret in repo[0].secrets],
            vc=VCResponse.from_orm(repo[0].vc) if repo[0].vc else None
        )
        for repo in repo_results
    ]

    return {
        "data": repo_responses if repo_responses else [],
        **pagination['meta']
    }


async def get_available_filters() -> List[FilterOption]:
    return [
        FilterOption(key="vc_ids", label="Version Control ID", type="integer", searchable=True),
        FilterOption(key="repo_ids", label="Repository ID", type="integer", searchable=True),
        FilterOption(key="authors", label="Authors", type="text", searchable=True),
        FilterOption(key="created_after", label="Created After", type="datetime", searchable=True),
        FilterOption(key="created_before", label="Created Before", type="datetime", searchable=True),
        
    ]


async def get_filter_values(
    db: AsyncSession,
    filter_key: str,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> dict:
    query = None

    if filter_key == "vc_ids":
        query = select(Repo.vc_id, Repo.vc_name, func.count(Repo.id)).group_by(Repo.vc_id, Repo.vc_name)
        if search:
            query = query.where(Repo.vc_id == int(search))

    elif filter_key == "repo_ids":
        query = select(Repo.id, Repo.name, func.count(Repo.id)).group_by(Repo.id, Repo.name)
        if search:
            query = query.where(Repo.id == int(search))

    elif filter_key == "created_at":
        query = select(
            func.date(Repo.created_at), func.count(Repo.id)
        ).group_by(func.date(Repo.created_at))
        if search:
            query = query.where(func.date(Repo.created_at) == search)

    elif filter_key == "repo_name":
        query = select(Repo.name, func.count(Repo.id)).group_by(Repo.name)
        if search:
            query = query.where(Repo.name.ilike(f"%{search}%"))

    elif filter_key == "authors":
        query = select(Repo.author, func.count(Repo.id)).group_by(Repo.author)
        if search:
            query = query.where(Repo.author.ilike(f"%{search}%"))

    elif filter_key == "sort_by":
        return {
            "values": [
                "vc_id",
                "repo_id",
                "secrets_count",
                "vulnerability_count",
                "created_at",
                "score_normalized"]}

    elif filter_key == "order_by":
        return {
            "values": [
                {"value": "asc", "label": "asc"},
                {"value": "desc", "label": "desc"}
            ],
            "total_count": 2
        }

    else:
        raise ValueError("Unsupported filter key")

    total_count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar()

    pagination = paginate(query, total_count, page, limit)
    paginated_query = pagination['query']

    result = await db.execute(paginated_query)
    rows = result.all()

    if filter_key == "vc_ids":
        values = [{"value": row[0], "label": row[1]} for row in rows]
    elif filter_key == "repo_ids":
        values = [{"value": row[0], "label": row[1]} for row in rows]
    elif filter_key == "author":
        values = [{"value": row[0], "label": row[0]} for row in rows]
    else:
        values = [{"value": row[0], "label": str(row[1])} for row in rows]

    return {
        "values": values,
        "total_count": total_count
    }


async def update_sca_branches(db: AsyncSession, repo_id: int, sca_branches: List[str], current_user: Optional[User] = None) -> Repo:
    repo = await get_repo_by_id(db, repo_id)

    repo.sca_branches = sca_branches
    repo.updated_by = current_user.id
    await db.commit()
    await db.refresh(repo)
    return repo


async def generate_sbom_for_repo(
    db: AsyncSession,
    repo_id: int,
    branch: Optional[str] = None  # Optional branch argument
) -> dict:
    try:
        # Retrieve the repository by ID
        repo_result = await db.execute(select(Repo).filter(Repo.id == repo_id))
        repo = repo_result.scalar_one_or_none()

        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No repository found with ID {repo_id}"
            )

        vc_result = await db.execute(select(VC).filter(VC.id == repo.vc_id))
        vc = vc_result.scalar_one_or_none()

        if not vc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version control information not found for repository ID {repo_id}"
            )

        repo_identifier = os.path.splitext(repo.repoUrl.rstrip('/').split('/')[-1])[0]
        # Clone the repository (with branch if provided)
        if branch:
            target_dir = clone_repo(
                vc_type=repo.vctype.value,
                repo_name=repo_identifier,
                clone_url=repo.repoUrl,
                token=vc.token,
                branch_name=branch  # Use specified branch
            )
        else:
            target_dir = clone_repo(
                vc_type=repo.vctype.value,
                repo_name=repo_identifier,
                clone_url=repo.repoUrl,
                token=vc.token
            )

        # Generate the SBOM (Software Bill of Materials)
        sbom_json = await generate_sbom(target_dir)
        delete_folder(target_dir)

        if not sbom_json:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate SBOM for the repository"
            )

        return {
            "repo_name": repo.name,
            "repo_url": repo.repoUrl,
            "branch": branch or "default branch",  # Return the branch used or "default branch"
            "sbom": sbom_json  # Returning the SBOM JSON
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to generate SBOM for the given repository or branch"
        )