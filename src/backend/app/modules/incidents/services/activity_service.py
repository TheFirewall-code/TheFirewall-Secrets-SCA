from typing import Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, asc

from app.modules.incidents.models.activity_model import Activity
from app.modules.incidents.schemas.activity_schemas import ActivityCreate, ActivityResponse
from app.modules.user.models.user import User
from app.utils.pagination import paginate
from sqlalchemy.exc import NoSuchColumnError
from sqlalchemy.orm import joinedload

async def add_activity(
    db: AsyncSession,
    activity_data: ActivityCreate,
    current_user: Optional[User] = None
) -> ActivityResponse:
    stmt = select(Activity).filter(
        Activity.incident_id == activity_data.incident_id
    ).order_by(desc(Activity.created_at)).limit(1)

    result = await db.execute(stmt)
    last_activity = result.scalars().first()
    old_value = last_activity.new_value if last_activity else None

    new_activity = Activity(
        incident_id=activity_data.incident_id,
        user_id=current_user.id if current_user else None,
        action=activity_data.action,
        old_value=old_value,
        new_value=activity_data.new_value,
        created_at=datetime.utcnow()
    )

    db.add(new_activity)
    await db.commit()
    await db.refresh(new_activity)

    return new_activity


async def get_activities(
    db: AsyncSession,
    incident_id: int,
    page: int = 1,
    page_size: int = 10,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    sort_by: str = "created_at",
    order_by: str = "desc",
) -> Dict[str, Any]:
    # Base query
    stmt = select(Activity).filter(Activity.incident_id == incident_id)
    
    # Join with User table to get username
    stmt = stmt.options(joinedload(Activity.user))  # Assuming relationship `user` exists

    # Apply filters
    if action:
        stmt = stmt.filter(Activity.action == action)
    if user_id:
        stmt = stmt.filter(Activity.user_id == user_id)
    if old_value:
        stmt = stmt.filter(Activity.old_value == old_value)
    if new_value:
        stmt = stmt.filter(Activity.new_value == new_value)

    # Apply sorting
    try:
        column_to_sort = getattr(Activity, sort_by, None)
        if column_to_sort is None:
            raise NoSuchColumnError(f"Column '{sort_by}' does not exist in the Activity model.")

        if order_by.lower() == "desc":
            stmt = stmt.order_by(desc(column_to_sort))
        else:
            stmt = stmt.order_by(asc(column_to_sort))
    except NoSuchColumnError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Count total records
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count_result = await db.execute(count_stmt)
    total_count = total_count_result.scalar()

    # Paginate the results
    paginated_result = paginate(stmt, total_count, page, page_size)
    result = await db.execute(paginated_result["query"])
    activities = result.scalars().all()

    if not activities:
        raise HTTPException(status_code=404, detail="No activities found.")

    # Map usernames to activities
    data = [
        {
            "id": activity.id,
            "action": activity.action,
            "user_id": activity.user_id,
            "username": activity.user.username if activity.user else None,
            "old_value": activity.old_value,
            "new_value": activity.new_value,
            "created_at": activity.created_at,
        }
        for activity in activities
    ]

    return {
        "data": data,
        **paginated_result["meta"]
    }


def get_activity_by_id(db: Session, activity_id: int) -> ActivityResponse:
    activity = db.query(Activity).filter(Activity.id == activity_id).first()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found.")

    return ActivityResponse.from_orm(activity)
