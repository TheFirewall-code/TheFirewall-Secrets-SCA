from datetime import datetime
from sqlalchemy.orm import Session
from app.utils.pagination import paginate
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from app.modules.user.models.user import User
from typing import Dict, List

from app.modules.incidents.schemas.activity_schemas import ActivityCreate
from app.modules.incidents.services.activity_service import add_activity

from app.modules.incidents.models.comment_model import Comments
from app.modules.incidents.schemas.comment_schemas import CommentBase, CommentResponse
from app.modules.incidents.services.incident_service import get_incident_by_id
from app.modules.incidents.schemas.incident_schemas import IncidentResponse
from app.modules.incidents.models.activity_model import Action


async def create_comment(
        db: Session,
        comment: CommentBase,
        current_user: User) -> CommentResponse:
    # Create a new comment in the database
    new_comment = Comments(
        content=comment.content,
        incident_id=comment.incident_id,
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )

    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)

    # Fetch the incident details
    incident: IncidentResponse = await get_incident_by_id(db, comment.incident_id)
    status = incident.status.value

    # Create an activity for the status update
    activity_data = ActivityCreate(
        incident_id=comment.incident_id,
        action=Action.COMMENT_ADDED,
        new_value=status,
        comment_id=new_comment.id
    )
    await add_activity(db=db, activity_data=activity_data, current_user=current_user)

    # Return a CommentResponse including id and created_at
    return CommentResponse(
        id=new_comment.id,
        content=new_comment.content,
        incident_id=new_comment.incident_id,
        user_id=new_comment.user_id,
        created_at=new_comment.created_at
    )


async def get_comments_by_incident_id(
        db: Session,
        incident_id: int,
        page: int,
        limit: int) -> Dict:

    total_count = await db.scalar(select(func.count(Comments.id)).filter(Comments.incident_id == incident_id))

    comments_query = select(Comments).filter(
        Comments.incident_id == incident_id).order_by(
        Comments.created_at.desc())

    pagination_result = paginate(comments_query, total_count, page, limit)

    paginated_comments = await db.execute(pagination_result["query"])
    comments = paginated_comments.scalars().all()

    comment_responses: List[CommentResponse] = [
        CommentResponse(
            id=comment.id,
            content=comment.content,
            incident_id=comment.incident_id,
            user_id=comment.user_id,
            created_at=comment.created_at
        ) for comment in comments
    ]

    return {
        "data": comment_responses,
        **pagination_result["meta"]
    }
