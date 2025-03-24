# SQLAlchemy Imports
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import array
from sqlalchemy import asc, desc, or_

# FastAPI and Typing Imports
from fastapi import HTTPException
from typing import Optional, List

# App-Specific Imports
from app.modules.whitelist.model.whitelist_model import Whitelist, WhitelistComment
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from app.utils.whitelist.add_vulnerability_str import add_vulnerability_str
from app.modules.whitelist.schema.whitelist_schema import (
    WhitelistCreate,
    WhitelistUpdate,
    WhitelistResponse,
    WhitelistCommentResponse,
    VCSInfo,
    RepoInfo,
    WhitelistUpdateResponse,
    WhiteListType)
from app.utils.pagination import paginate
from app.modules.user.models.user import User
from app.modules.vc.models.vc import VC
from app.modules.repository.models.repository import Repo

# Utils for secrets
from app.utils.whitelist.add_secret_str import add_secret_str
from app.utils.whitelist.update_secret import update_secret, update_vulnerability
from app.modules.vulnerability.models.vulnerability_model import Vulnerability
from app.core.logger import logger
import subprocess
import json

# Add a comment and return the comment ID
async def add_comment(db: Session, comment_text: str, created_by: int) -> int:
    new_comment = WhitelistComment(comment=comment_text, created_by=created_by)
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    return new_comment.id


# Add a new whitelist entry
async def add_whitelist(
    db: AsyncSession,
    whitelist_data: WhitelistCreate,
    current_user: User
):
    """
    Create a new whitelist entry.

    - If `whitelist_data.name` is provided, we'll check if there's
      an existing whitelist with the same name+type.
    - We can also accept repos, vcs, or global, in any combination.
    """

    if not whitelist_data.name and not whitelist_data.repos and not whitelist_data.vcs:
        raise HTTPException(
            status_code=400,
            detail="Missing either name or repos or vcs"
        )


    comment_ids = []
    if whitelist_data.comment:
        comment_id = await add_comment(
            db,
            whitelist_data.comment,
            current_user.id if current_user else 1
        )
        comment_ids.append(comment_id)

    new_whitelist = Whitelist(
        type=whitelist_data.type,
        name=whitelist_data.name,
        vcs=whitelist_data.vcs,
        repos=whitelist_data.repos,
        comments=comment_ids,
        active=whitelist_data.active,
        global_=whitelist_data.global_,
        created_by=current_user.id if current_user else 1,
        updated_by=current_user.id if current_user else 1
    )

    db.add(new_whitelist)
    await db.commit()
    await db.refresh(new_whitelist)

    # Only update secrets if type is SECRET
    secrets_updated = 0
    if whitelist_data.type == "SECRET":
        print("Whitelisting a secret")
        secrets_updated = await add_secret_str(db, new_whitelist)

    vulnerabilities_updated = 0
    if whitelist_data.type == "VULNERABILITY":
        print("Whitelisting a vul")
        vulnerabilities_updated = await add_vulnerability_str(db, new_whitelist)

    return WhitelistUpdateResponse(
        name=whitelist_data.name,
        vcs=whitelist_data.vcs,
        repos=whitelist_data.repos,
        created_by=current_user.id if current_user else 1,
        updated_by=current_user.id if current_user else 1,
        id=new_whitelist.id,
        secrets_updated=secrets_updated,
        vulnerabilities_updated=vulnerabilities_updated,
        comments=comment_ids,
        created_on=new_whitelist.created_on 
    )


async def get_whitelist(
    db: AsyncSession,
    vc_ids: Optional[List[int]] = None,
    repo_ids: Optional[List[int]] = None,
    name: Optional[str] = None,
    search: Optional[str] = None,
    type: WhiteListType = None,
    page: int = 1,
    limit: int = 10,
    sort_by: str = "id",
    order_by: str = "asc",
    repo_whitelist=False
):  
    # Initial whitelist query
    query = select(Whitelist).filter(Whitelist.active)

    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        query = query.filter(func.lower(Whitelist.name).like(f"%{search_lower}%"))

    if type:
        query = query.filter(Whitelist.type == type)

    # Apply filters for VCS and repositories
    if vc_ids:
        query = query.filter(array(vc_ids).overlap(Whitelist.vcs))
    if repo_ids:
        query = query.filter(array(repo_ids).overlap(Whitelist.repos))
    if name:
        query = query.filter(Whitelist.name == name)
    if not repo_whitelist:
        query = query.filter(Whitelist.name.isnot(None))  # Corrected syntax for IS NOT NULL
    else:
        query = query.filter(Whitelist.name.is_(None))  # Corrected syntax for IS NULL

    # Sorting
    sort_column = getattr(Whitelist, sort_by, Whitelist.id)
    query = query.order_by(desc(sort_column) if order_by == "desc" else asc(sort_column))

    # Get total count for pagination
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(total_count_query)

    # Pagination logic
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit
    paginated_query = query.offset(offset).limit(limit)
    results = await db.scalars(paginated_query)
    whitelists = results.all()

    # Fetch VCS and repository details
    vcs_ids = {vcs_id for w in whitelists for vcs_id in w.vcs}
    repos_ids = {repo_id for w in whitelists for repo_id in w.repos}

    vcs_query = select(VC.id, VC.name).where(VC.id.in_(vcs_ids))
    vcs_result = await db.execute(vcs_query)
    vcs_dict = dict(vcs_result.fetchall())

    repos_query = select(Repo.id, Repo.name).where(Repo.id.in_(repos_ids))
    repos_result = await db.execute(repos_query)
    repos_dict = dict(repos_result.fetchall())

    # Fetch comments with user details
    all_comment_ids = {comment_id for w in whitelists if w.comments for comment_id in w.comments}

    # Query to fetch comments with sorting by created_on (latest first)
    comments_query = (
        select(WhitelistComment, User.id, User.username)
        .join(User, WhitelistComment.created_by == User.id)
        .where(WhitelistComment.id.in_(all_comment_ids))
        .order_by(desc(WhitelistComment.created_on))
    )
    comments_result = await db.execute(comments_query)

    # Organizing comments into a dictionary for quick access
    comments_dict = {
        comment.id: {
            "comment": comment.comment,
            "created_on": comment.created_on,
            "created_by": user_id,
            "user": {"id": user_id, "name": user_name}
        }
        for comment, user_id, user_name in comments_result.all()
    }


    # Construct whitelist responses
    whitelist_responses = [
        WhitelistResponse(
            id=w.id,
            type=w.type,
            name=w.name,
            active=w.active,
            global_=w.global_,
            vcs=[VCSInfo(id=vc_id, name=vcs_dict.get(vc_id)) for vc_id in w.vcs if vc_id in vcs_dict],
            repos=[RepoInfo(id=repo_id, name=repos_dict.get(repo_id)) for repo_id in w.repos if repo_id in repos_dict],
            comments=[
                WhitelistCommentResponse(
                    id=comment_id,
                    comment=comments_dict[comment_id]["comment"],
                    created_on=comments_dict[comment_id]["created_on"],
                    created_by=comments_dict[comment_id]["user"]["name"],
                    user_id=comments_dict[comment_id]["user"]["id"]
                )
                for comment_id in w.comments if comment_id in comments_dict
            ],
            created_on=w.created_on
        )
        for w in whitelists
    ]

    return {
        "data": whitelist_responses,
        "total_count": total_count,
        "current_page": page,
        "total_pages": total_pages,
        "current_limit": limit
    }


async def update_whitelist(
    db: AsyncSession,
    whitelist_id: int,
    whitelist_data: WhitelistUpdate,
    current_user: User
):
    stmt = select(Whitelist).where(Whitelist.id == whitelist_id)
    result = await db.execute(stmt)
    whitelist_record = result.scalars().first()

    if not whitelist_record:
        raise HTTPException(status_code=404, detail="Whitelist not found")

    # Ensure comments is always a list
    if not isinstance(whitelist_record.comments, list):
        whitelist_record.comments = []

    # If a new comment is provided, add it
    if whitelist_data.comment:
        comment_id = await add_comment(db, whitelist_data.comment, current_user.id)
        whitelist_record.comments.append(comment_id)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(whitelist_record, "comments")

    # Update whitelist record fields (e.g., name, active, global_, repos, vcs, type)
    for key, value in whitelist_data.dict(exclude_unset=True).items():
        if key != "comment":  # already handled above
            setattr(whitelist_record, key, value)

    # Decide whether we are updating secrets or vulnerabilities
    secrets_updated_count = 0
    vulnerabilities_updated_count = 0

    # If the type is SECRET, update secrets based on the new whitelist data
    if whitelist_record.type == WhiteListType.SECRET:
        secrets_updated_count = await update_secret(
            db=db,
            whitelist_id=whitelist_record.id,
            active=whitelist_record.active,
            repos=whitelist_record.repos,
            vcs=whitelist_record.vcs,
            is_global=whitelist_record.global_
        )

    # If the type is VULNERABILITY, update vulnerabilities based on the new whitelist data
    elif whitelist_record.type == WhiteListType.VULNERABILITY:
        vulnerabilities_updated_count = await update_vulnerability(
            db=db,
            whitelist_id=whitelist_record.id,
            active=whitelist_record.active,
            repos=whitelist_record.repos,
            vcs=whitelist_record.vcs,
            is_global=whitelist_record.global_
        )

    await db.commit()
    await db.refresh(whitelist_record)

    return WhitelistUpdateResponse(
        id=whitelist_record.id,
        name=whitelist_record.name,
        created_on=whitelist_record.created_on,
        created_by=whitelist_record.created_by,
        updated_by=current_user.id,
        secrets_updated=secrets_updated_count,
        vulnerabilities_updated=vulnerabilities_updated_count,
        type=whitelist_record.type,
        comments=whitelist_record.comments,
    )

# Check if a secret is whitelisted for a repo
async def is_whitelisted(
        db: Session,
        type: WhiteListType,
        name: Optional[str] = None,
        repo_id: Optional[int] = None,
        vc_id: Optional[int] = None,
) -> Optional[int]:
    """
        Check if an entity (e.g., secret or vulnerability) is whitelisted.

        Logic:
        - If `name` is provided, check for a whitelist with `name`, `repo_id`, and `vc_id`.
        - If `name` is provided, check for a global whitelist with `name`.
        - Check for a whitelist with `repo_id` and/or `vc_id`, with `name` being NULL.
        - Returns a dictionary with `whitelist_id` and `whitelisted` (boolean).
        """

    # 1. Check for a global whitelist with the given name
    if name:
        global_query = select(Whitelist).filter(
            Whitelist.type == type,
            Whitelist.active == True,
            Whitelist.global_ == True,
            Whitelist.name == name
        )
        global_result = await db.scalars(global_query)
        global_whitelist = global_result.first()
        if global_whitelist:
            return global_whitelist.id

    # 2. Check for a specific whitelist with name, repo_id, and/or vc_id
    if name:
        specific_query = select(Whitelist).filter(
            Whitelist.type == type,
            Whitelist.active == True,
            Whitelist.name == name,
            or_(
                Whitelist.repos.any(repo_id) if repo_id else False,
                Whitelist.vcs.any(vc_id) if vc_id else False,
            )
        )
        specific_result = await db.scalars(specific_query)
        specific_whitelist = specific_result.first()
        if specific_whitelist:
            return specific_whitelist.id

    # 3. Check for a whitelist with repo_id and/or vc_id where name is NULL
    generic_query = select(Whitelist).filter(
        Whitelist.type == type,
        Whitelist.active == True,
        Whitelist.name.is_(None),
        or_(
            Whitelist.repos.any(repo_id) if repo_id else False,
            Whitelist.vcs.any(vc_id) if vc_id else False,
        )
    )
    generic_result = await db.scalars(generic_query)
    generic_whitelist = generic_result.first()
    if generic_whitelist:
        return generic_whitelist.id

    # 4. Not whitelisted
    return None


async def get_filters() -> dict:
    filters = {
        "filters": [
            {"key": "vc_ids", "label": "Version Controls", "type": "api", "searchable": True},
            {"key": "repo_ids", "label": "Repositories", "type": "api", "searchable": True},
            {"key": "name", "label": "Name", "type": "text", "searchable": True},
        ]
    }
    return filters


async def paginate(query, total_count, page, page_size):
    """Paginate the given query."""
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    total_pages = (total_count + page_size - 1) // page_size

    return {
        "query": query,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
        },
    }

async def get_filter_values(
    db: Session,
    value: str,
    page: int = 1,
    page_size: int = 10
):
    if value == "vcs_ids":
        query = select(Whitelist.vcs).distinct()
    elif value == "repo_ids":
        query = select(Whitelist.repos).distinct()
    elif value == "name":
        query = select(Whitelist.name).distinct()
    else:
        return None

    # Execute the query and fetch results
    result = await db.scalars(query)

    if value in ["vcs_ids", "repo_ids"]:
        # Flatten arrays and remove duplicates
        flat_values = {item for sublist in result.all() if sublist for item in sublist}
        sorted_values = sorted(flat_values)
    elif value == "name":
        sorted_values = [{"value": item, "label": item} for item in sorted(result.all()) if item]
    else:
        sorted_values = sorted({item for item in result if item})

    total_count = len(sorted_values)

    if value in ["vcs_ids", "repo_ids"]:
        start = (page - 1) * page_size
        end = start + page_size
        paginated_values = sorted_values[start:end]
    else:
        paginated_values = sorted_values

    # Return results with total count
    return {
        "values": paginated_values,
        "total": total_count
    }


async def sca_whitelist_fix_cron(db: AsyncSession):
    logger.info("Starting SCA whitelist fix cron job.")

    query = (
        select(Whitelist)
        .filter(Whitelist.active == True, Whitelist.type == WhiteListType.VULNERABILITY)
        .filter(Whitelist.name.isnot(None))
    )

    # Fetch active whitelists of type VULNERABILITY
    result = await db.execute(query)
    whitelists = result.scalars().all()

    logger.info(f"Fetched {len(whitelists)} active whitelists for processing.")

    for whitelist in whitelists:
        try:
            logger.info(f"Processing whitelist ID {whitelist.id} with name {whitelist.name}.")

            # Query the Vulnerability table for matching vulnerabilities
            vuln_query = select(Vulnerability).filter(
                or_(
                    Vulnerability.vulnerability_id == whitelist.name,
                    Vulnerability.cve_id == whitelist.name
                )
            )
            vuln_result = await db.execute(vuln_query)
            vulnerability = vuln_result.scalars().first()

            if not vulnerability:
                logger.warning(f"No matching vulnerability found for whitelist {whitelist.name}. Skipping.")
                continue

            logger.info(f"Found vulnerability {vulnerability.vulnerability_id} for whitelist {whitelist.name}.")

            # Run the Grype command to check for fixes
            cmd = ["grype", "db", "search", whitelist.name, "-o", "json"]
            logger.info(f"Running Grype command: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse the output of the Grype command
            grype_output = json.loads(process.stdout)
            print(grype_output)
            fix_available = any(
                item.get("Fix", {}).get("State") == "fixed" for item in grype_output
            )

            logger.info(f"Fix available {fix_available}")

            # If a fix is available and the whitelist was previously active, deactivate it
            if fix_available and not vulnerability.fix_available:
                logger.info(f"Fix available for vulnerability {vulnerability.vulnerability_id}. Updating records.")
                vulnerability.fix_available = True  # Update the vulnerability record
                whitelist.active = False
                logger.info(f"Deactivating whitelist ID {whitelist.id} due to available fix.")

                whitelist_data = WhitelistUpdate(
                    active=False,
                    comment="Whitelist disabled due to an available fix for the vulnerability."
                )
                await update_whitelist(db, whitelist_id=whitelist.id, whitelist_data=whitelist_data,current_user=User(id=1))
                await db.commit()
                logger.info(f"Whitelist ID {whitelist.id} successfully updated and deactivated.")
            else:
                print('No changes')

        except subprocess.CalledProcessError as e:
            logger.error(f"Error running Grype for {vulnerability.vulnerability_id}: {e.stderr}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Grype output for {vulnerability.vulnerability_id}.")
        except Exception as e:
            logger.error(f"Unexpected error while processing whitelist ID {whitelist.id}: {str(e)}")

    logger.info("SCA whitelist fix cron job completed.")