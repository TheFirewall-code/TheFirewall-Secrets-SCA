from app.modules.jiraAlerts.models.model import JiraAlert
from app.modules.jiraAlerts.schemas.schema import JiraAlertCreate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
import json
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional
import os
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

# Load FRONTEND_URL from .env
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")




async def get_jira_alert(db: AsyncSession):
    result = await db.execute(select(JiraAlert))
    return result.scalars().first()  # `.scalars()` unwraps the result




async def create_jira_alert(db: AsyncSession, alert: JiraAlertCreate):
    existing_alert = await get_jira_alert(db)
    if existing_alert:
        return None  # Or raise an exception
    new_alert = JiraAlert(id="default_alert", base_url=alert.base_url, user_email=alert.user_email, api_token=alert.api_token, project_key=alert.project_key, is_active=alert.is_active)
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)
    return new_alert

async def update_jira_alert(db: AsyncSession, alert: JiraAlertCreate):
    existing_alert = await get_jira_alert(db)
    if not existing_alert:
        return None
    existing_alert.base_url = alert.base_url
    existing_alert.user_email = alert.user_email
    existing_alert.api_token = alert.api_token
    existing_alert.project_key = alert.project_key
    existing_alert.is_active = alert.is_active
    await db.commit()
    await db.refresh(existing_alert)
    return existing_alert

async def delete_jira_alert(db: AsyncSession):
    existing_alert = await get_jira_alert(db)
    if existing_alert:
        existing_alert.is_active = False  # Soft delete by setting is_active to False
        await db.commit()
    return existing_alert

async def send_alert_to_jira(
    db: AsyncSession,
    severity_count: dict,
    sec_count: int,
    vul_count: int,
    repo_name: str,
    scan_type: str,
    pr_id: Optional[int] = None,
    commit_id: Optional[int] = None,
    repo_id: Optional[int] = None,
    pr_scan_id: Optional[int] = None,
    pr_id_internal:Optional[int] = None,
):
    try:
        if sec_count == 0 and vul_count == 0:
            return

        # Fetch Jira settings from the database
        try:
            settings = await db.execute(select(JiraAlert).where(JiraAlert.is_active == True))
            settings = settings.scalars().first()
            print("Jira Settings:", settings)
        except Exception as e:
            print(f"Error fetching Jira settings: {e}")
            return

        if not settings:
            print("Jira settings are not configured.")
            return

        # Map scan_type to a more user-friendly description
        scan_type_label = {
            "pr_scan": "Recent PR Scan",
            "live_commit": "Live Commit Scan",
            "repo_scan": "Repository Scan"
        }.get(scan_type, scan_type)

        # Customize description with severity details
        severity_text = ""

        # Process secrets
        if "secret" in severity_count and isinstance(severity_count["secret"], list):
            secret_details = "\n".join(
                [f"{item['severity'].title()}: {item['count']}" for item in severity_count["secret"] if item["count"] > 0]
            )
            if secret_details:
                severity_text += "Secrets:\n" + secret_details

        # Process vulnerabilities
        if "vulnerability" in severity_count and isinstance(severity_count["vulnerability"], dict):
            vulnerability_details = "\n".join(
                [f"{severity.title()}: {count}" for severity, count in severity_count["vulnerability"].items() if count > 0]
            )
            if vulnerability_details:
                if severity_text:
                    severity_text += "\n\n"  # Add spacing between sections
                severity_text += "Vulnerabilities:\n" + vulnerability_details

        # Handle no issues found
        if not severity_text:
            severity_text = "No issues found."

        print("Severity Text:", severity_text)

        # Build query parameters for incident links
        query_params = {}
        if pr_id:
            query_params['pr_ids'] = pr_id_internal
        if commit_id:
            query_params['commits'] = commit_id
        if repo_id:
            query_params['repo_ids'] = repo_id

        secret_incident_link = f"{FRONTEND_URL}/secret/incidents?{urlencode(query_params)}" if sec_count > 0 else None
        vul_incident_link = f"{FRONTEND_URL}/sca/incidents?{urlencode(query_params)}" if vul_count > 0 else None

        # Prepare the payload for the Jira alert
        jira_payload = {
            "fields": {
                "project": {
                    "key": settings.project_key
                },
                "summary": f"[TheFirewall] {sec_count + vul_count} issues found in {repo_name}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Issues were found in {repo_name} during a {scan_type_label}.\n\n{severity_text}"
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "• For more details, click "
                                },
                                {
                                    "type": "text",
                                    "text": "here",
                                    "marks": [{"type": "link", "attrs": {"href": secret_incident_link}}] if secret_incident_link else []
                                }
                            ]
                        }
                    ]
                },
                "priority": {
                    "name": "High"
                },
                "issuetype": {
                    "name": "Task"
                }
            }
        }

        # Add vulnerability link if present
        if vul_incident_link:
            jira_payload["fields"]["description"]["content"].append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "• For vulnerabilities, click "
                    },
                    {
                        "type": "text",
                        "text": "here",
                        "marks": [{"type": "link", "attrs": {"href": vul_incident_link}}]
                    }
                ]
            })

        if pr_id or commit_id or repo_id:
            identifiers = []
            if pr_id:
                identifiers.append(f"Pull Request ID: {pr_id}")
            if commit_id:
                identifiers.append(f"Commit ID: {commit_id}")
            jira_payload["fields"]["description"]["content"][0]["content"].append({
                "type": "text",
                "text": "\n• " + "\n• ".join(identifiers)
            })
        print("Jira Payload:", jira_payload)

        # Send the alert to Jira
        try:
            auth = HTTPBasicAuth(settings.user_email, settings.api_token)
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            url = f"{settings.base_url.rstrip('/')}/rest/api/3/issue"
            response = requests.post(url, headers=headers, json=jira_payload, auth=auth)
            print("Jira Response Status Code:", response.status_code)
            print("Jira Response Text:", response.text)

            if response.status_code == 201:
                print("Jira Issue Created Successfully")
                return {"message": "Alert sent successfully to Jira"}
            else:
                raise HTTPException(status_code=response.status_code, detail=response.json())
        except Exception as e:
            print(f"Error sending Jira alert: {e}")
            raise e
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return {"message": f"An error occurred: {str(e)}"}
