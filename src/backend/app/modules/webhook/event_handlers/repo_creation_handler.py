from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.future import select

from app.modules.repository.models.repository import Repo
from app.modules.repository.repository_service import scan_repo_by_id
from app.modules.vc.vc_service import get_vc


async def repo_creation_handler(db, vc_id, event_info):
    # Extract relevant information from event_info
    repo_name = event_info["repo_name"]
    clone_url = event_info["clone_url"]
    author = event_info["author"]
    other_details = event_info.get("other_details", None)

    # Retrieve version control info
    vc = await get_vc(db, vc_id)

    existing_repo_result = await db.execute(
        select(Repo).filter(Repo.name == repo_name, Repo.vc_id == vc_id)
    )
    existing_repo = existing_repo_result.scalars().first()

    if not existing_repo:
        new_repo = Repo(
            vc_id=vc.id,
            vctype=vc.type,
            name=repo_name,
            repoUrl=clone_url,
            author=author,
            other_repo_details=other_details
        )
        db.add(new_repo)
        await db.commit()
        await db.refresh(new_repo)

        await scan_repo_by_id(db, new_repo.id)
        return JSONResponse(
            status_code=200, content={
                "message": "Repo added and scanned successfully"})
    else:
        return JSONResponse(
            status_code=400, content={
                "message": "Repository already exists"})
