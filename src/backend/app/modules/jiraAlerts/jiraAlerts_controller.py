from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.modules.jiraAlerts.jiraAlerts_service import (
    get_jira_alert, 
    create_jira_alert, 
    update_jira_alert, 
    delete_jira_alert,
    send_alert_to_jira
)
from app.modules.jiraAlerts.schemas.schema import JiraAlertCreate, JiraAlertResponse
from app.core.db import get_db

from app.modules.auth.auth_utils import role_required, get_current_user
from app.modules.user.models.user import UserRole

router = APIRouter(prefix="/jira-alert", tags=['Jira Alerts'])

@router.post("/", response_model=JiraAlertResponse, dependencies=[Depends(role_required([UserRole.admin]))])
async def create_alert(alert: JiraAlertCreate, db: Session = Depends(get_db)):
    db_alert = await create_jira_alert(db, alert)
    if not db_alert:
        raise HTTPException(status_code=400, detail="Only one alert is allowed.")
    return db_alert

@router.get("/", response_model=JiraAlertResponse, dependencies=[Depends(role_required([UserRole.admin]))])
async def read_alert(db: Session = Depends(get_db)):
    alert = await get_jira_alert(db)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert

@router.put("/", response_model=JiraAlertResponse, dependencies=[Depends(role_required([UserRole.admin]))])
async def update_alert(alert: JiraAlertCreate, db: Session = Depends(get_db)):
    updated_alert = await update_jira_alert(db, alert)
    if not updated_alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return updated_alert

@router.delete("/", response_model=JiraAlertResponse, dependencies=[Depends(role_required([UserRole.admin]))])
async def delete_alert(db: Session = Depends(get_db)):
    deleted_alert = await delete_jira_alert(db)
    if not deleted_alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return deleted_alert


@router.post("/send", dependencies=[Depends(role_required([UserRole.admin]))])
async def send_alert(db: Session = Depends(get_db)):
    result = await send_alert_to_jira(db)
    return result