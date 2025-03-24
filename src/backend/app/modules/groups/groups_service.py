from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from app.modules.groups.models.group_model import Group
from app.modules.repository.models.repository import Repo
from app.modules.groups.schemas.group_schema import CreateGroupSchema, RepoFilterSchema
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlalchemy import func, update, desc, asc
from app.utils.pagination import paginate
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.groups.models.group_model import Group
from app.modules.groups.models.group_model import Repo
from sqlalchemy.orm import joinedload


async def create_group(
        db: AsyncSession,
        group_data: CreateGroupSchema,
        current_user) -> Group:
    group = Group(
        name=group_data.name,
        description=group_data.description,
        created_by=current_user.id,
        updated_by=current_user.id
    )
    if group_data.repos:
        repos = await db.execute(select(Repo).where(Repo.id.in_(group_data.repos)))
        group.repos = repos.scalars().all()
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def get_group_by_id(db: AsyncSession, group_id: int) -> Group:
    query = select(Group).where(
        Group.id == group_id, Group.active == True
    ).options(selectinload(Group.repos))
    result = await db.execute(query)
    
    group = result.scalars().first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    return group


async def get_all_groups(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    repo_ids: Optional[List[int]] = None,
    sort_by: Optional[str] = "name",
    order_by: Optional[str] = "asc"
) -> dict:
    query = select(
        Group,
        func.count(Repo.id).label("repo_count")
    ).outerjoin(Group.repos).where(Group.active == True).group_by(Group.id)
    if search:
        query = query.where(Group.name.ilike(f"%{search}%"))
    if repo_ids:
        query = query.where(Group.repos.any(Repo.id.in_(repo_ids)))
    if sort_by == "repo_count":
        sort_column = func.count(Repo.id)
    elif sort_by == "score":
        sort_column = Group.score_normalized
    elif sort_by == "created_at":
        sort_column = Group.created_on
    elif sort_by == "description":
        sort_column = Group.description
    else:
        sort_column = Group.name
    if order_by == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    total_count_result = await db.execute(select(func.count(Group.id)).where(Group.active == True))
    total_count = total_count_result.scalar()
    pagination = paginate(query, total_count, page, limit)
    paginated_query = pagination["query"]

    result = await db.execute(paginated_query)
    groups_with_count = result.all()

    # Prepare data
    group_responses = [
        {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "active": group.active,
            "repo_count": repo_count,
            "created_on": group.created_on,
            "created_by": group.created_by,
            "updated_by": group.updated_by,
            "score_normalized": group.score_normalized,
            "score_normalized_on": group.score_normalized_on
        }
        for group, repo_count in groups_with_count
    ]

    # Return data and metadata in a dictionary
    return {
        "data": group_responses if group_responses else [],
        **pagination["meta"]
    }



async def delete_group(db: AsyncSession, group_id: int, current_user) -> Group:
    group = await get_group_by_id(db, group_id)
    group.active = False
    group.updated_by = current_user.id
    await db.commit()
    await db.refresh(group)
    return group


async def get_repos_for_group(db: AsyncSession, group_id: int) -> dict:
    group = await get_group_by_id(db, group_id)
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "active": group.active,
        "created_on": group.created_on,
        "created_by": group.created_by,
        "updated_by": group.updated_by,
        "repos": [
            {
                "id": repo.id,
                "name": repo.name,
                "author": repo.author,
                "score_normalized": repo.score_normalized,
                "repoUrl": repo.repoUrl,
                "created_at": repo.created_at,
                "other_repo_details": repo.other_repo_details,
                "vc_type": repo.vctype.value if repo.vctype else None
            }
            for repo in group.repos
        ]
    }


async def add_repos_to_group(
        db: AsyncSession,
        group_id: int,
        repo_ids: list[int],
        current_user) -> Group:
    group = await get_group_by_id(db, group_id)
    new_repos = await db.execute(select(Repo).where(Repo.id.in_(repo_ids)))
    existing_repo_ids = {repo.id for repo in group.repos}
    repos_to_add = [repo for repo in new_repos.scalars(
    ).all() if repo.id not in existing_repo_ids]

    if not repos_to_add:
        return {"id": group.id, "repos": [
            {"id": repo.id, "name": repo.name} for repo in group.repos]}

    group.repos.extend(repos_to_add)
    group.updated_by = current_user.id
    await db.commit()
    await db.refresh(group)
    return {"id": group.id, "repos": [
        {"id": repo.id, "name": repo.name} for repo in group.repos]}


async def remove_repos_from_group(
        db: AsyncSession,
        group_id: int,
        repo_ids: list[int],
        current_user) -> Group:
    group = await get_group_by_id(db, group_id)
    repos_to_remove = [repo for repo in group.repos if repo.id in repo_ids]

    if not repos_to_remove:
        return {"id": group.id, "repos": [
            {"id": repo.id, "name": repo.name} for repo in group.repos]}

    for repo in repos_to_remove:
        group.repos.remove(repo)

    group.updated_by = current_user.id
    await db.commit()
    await db.refresh(group)
    return {"id": group.id, "repos": [
        {"id": repo.id, "name": repo.name} for repo in group.repos]}


async def update_group(
    db: AsyncSession,
    group_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    repos_ids: Optional[List[int]] = None,
    current_user=None
):
    if not name and not description and not repos_ids:
        raise ValueError("At least one field (name, description, or repo_ids) must be provided to update.")

    # Update the group's basic info
    update_data = {"updated_by": current_user.id}
    if name:
        update_data["name"] = name
    if description:
        update_data["description"] = description
    query = update(Group).where(Group.id == group_id).values(**update_data).execution_options(synchronize_session="fetch")
    result = await db.execute(query)
    await db.commit()
    if result.rowcount == 0:
        raise NoResultFound(f"No group found with id {group_id}")

    # If repo_ids are provided, update repositories for the group
    if repos_ids is not None:
        group = await get_group_by_id(db, group_id)
        current_repo_ids = {repo.id for repo in group.repos}
        repos_to_add = [repo_id for repo_id in repos_ids if repo_id not in current_repo_ids]
        repos_to_remove = [repo for repo in group.repos if repo.id not in repos_ids]

        # Remove repos not in the new list
        for repo in repos_to_remove:
            group.repos.remove(repo)

        # Add new repos
        if repos_to_add:
            new_repos = await db.execute(select(Repo).where(Repo.id.in_(repos_to_add)))
            group.repos.extend(new_repos.scalars().all())

        group.updated_by = current_user.id
        await db.commit()
        await db.refresh(group)

    return {
        "status": "success",
        "message": "Group updated successfully",
        "group_id": group_id
    }



async def add_repos_to_group_by_filters(
        db: AsyncSession,
        group_id: int,
        repo_filters: RepoFilterSchema,
        current_user):
    query = select(Repo).where(True)
    if repo_filters.name:
        query = query.where(Repo.name.ilike(f"%{repo_filters.name}%"))
    if repo_filters.author:
        query = query.where(Repo.author.ilike(f"%{repo_filters.author}%"))
    if repo_filters.vc_id:
        query = query.where(Repo.vc_id == repo_filters.vc_id)
    repos_to_add = (await db.execute(query)).scalars().all()
    if not repos_to_add:
        raise HTTPException(
            status_code=404,
            detail="No repositories match the given filters.")
    return await add_repos_to_group(db, group_id, [repo.id for repo in repos_to_add], current_user)


async def remove_repos_from_group_by_filters(
        db: AsyncSession,
        group_id: int,
        repo_filters: RepoFilterSchema,
        current_user):
    query = select(Repo).where(True)
    if repo_filters.name:
        query = query.where(Repo.name.ilike(f"%{repo_filters.name}%"))
    if repo_filters.author:
        query = query.where(Repo.author.ilike(f"%{repo_filters.author}%"))
    if repo_filters.vc_id:
        query = query.where(Repo.vc_id == repo_filters.vc_id)
    repos_to_remove = (await db.execute(query)).scalars().all()
    if not repos_to_remove:
        raise HTTPException(
            status_code=404,
            detail="No repositories match the given filters.")
    return await remove_repos_from_group(db, group_id, [repo.id for repo in repos_to_remove], current_user)
