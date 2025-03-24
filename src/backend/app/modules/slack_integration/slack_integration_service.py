from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.modules.slack_integration.model.model import SlackIntegration
from app.modules.slack_integration.schema.schemas import CreateSlackIntegration, UpdateSlackIntegration
from fastapi import HTTPException
from app.modules.user.models.user import User
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.utils.string import mask_string
from typing import Optional
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

# Load FRONTEND_URL from .env
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


async def get_slack_integration(db: AsyncSession, mask=True):
    result = await db.execute(select(SlackIntegration).limit(1))
    slack = result.scalar_one_or_none()
    if not slack:
        return slack
    if mask:
        slack.token = mask_string(slack.token)
    return slack


async def create_slack_integration(
        db: AsyncSession,
        slack_integration_data: CreateSlackIntegration,
        current_user: User):
    # Check if a Slack integration already exists
    existing_integration = await db.execute(select(SlackIntegration))
    if existing_integration.scalars().first():
        raise HTTPException(status_code=400,
                            detail="A Slack integration already exists.")

    # Create new Slack integration if no existing one
    new_integration = SlackIntegration(
        token=slack_integration_data.token,
        channel=slack_integration_data.channel,
        active=slack_integration_data.active,
        created_by=current_user.id
    )
    db.add(new_integration)
    await db.commit()
    await db.refresh(new_integration)
    return new_integration


async def update_slack_integration(
    db: AsyncSession,
    slack_integration_data: UpdateSlackIntegration,
    current_user: User
):
    result = await db.execute(select(SlackIntegration).limit(1))
    integration = result.scalar_one_or_none()

    if not integration:
        return None

    if slack_integration_data.token is not None:
        integration.token = slack_integration_data.token
    if slack_integration_data.channel is not None:
        integration.channel = slack_integration_data.channel
    if slack_integration_data.active is not None:
        integration.active = slack_integration_data.active
    integration.updated_by = current_user.id
    await db.commit()
    await db.refresh(integration)
    return integration


async def fetch_and_notify_secrets(
    db: AsyncSession,
    severity_count: dict,
    repo_name: str,
    scan_type: str,
    pr_id: Optional[int] = None,
    commit_id: Optional[int] = None,
    repo_id: Optional[int] = None
):
    try:
        # Fetch Slack integration
        result = await db.execute(select(SlackIntegration).limit(1))
        slack_integration = result.scalar_one_or_none()

        if not slack_integration:
            return {"message": "No Slack integration found"}

        severity_colors = {
            "critical": ":red_circle:",
            "high": ":large_orange_circle:",
            "medium": ":large_orange_circle:",
            "low": ":large_green_circle:",
            "informational": ":large_blue_circle:",
            "unknown": ":white_circle:"
        }

        # Map scan_type to a more user-friendly description
        scan_type_label = {
            "pr_scan": "Recent PR Scan",
            "live_commit": "Live Commit Scan",
            "repo_scan": "Repository Scan"
        }.get(scan_type, scan_type)

        message = f"*{sum(severity_count.values())} secrets found* in *{repo_name}* during *{scan_type_label}*.\n"
        message += "\n".join(
            [f"{severity_colors[severity]} {severity.title()}: {count}"
             for severity, count in severity_count.items() if count > 0]
        )
        query_params = {
            "type": "secret"
        }
        if pr_id:
            query_params['pr_id'] = pr_id
        if commit_id:
            query_params['commit_id'] = commit_id
        if repo_id:
            query_params['repo_id'] = repo_id
        incident_link = f"{FRONTEND_URL}/incidents?{urlencode(query_params)}" if query_params else f"{FRONTEND_URL}/incidents"

        if pr_id:
            message += f"\n• Pull Request ID: `{pr_id}`"
        if commit_id:
            message += f"\n• Commit ID: `{commit_id}`"
        message += f"\n• <{incident_link}|More details>"

        client = WebClient(token=slack_integration.token)
        response = client.chat_postMessage(
            channel=slack_integration.channel,
            text=message
        )
        return {
            "message": "Notification sent",
            "channel": response["channel"],
            "ts": response["ts"],
            "status": response["ok"]
        }

    except SlackApiError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Slack API error: {e.response['error']}")
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}


async def notify_vulnerabilities(
    db: AsyncSession,
    severity_count: dict,
    repo_name: str,
    scan_type: str,
    pr_id: Optional[int] = None,
    commit_id: Optional[int] = None,
    repo_id: Optional[int] = None
):
    try:
        # Fetch Slack integration
        result = await db.execute(select(SlackIntegration).limit(1))
        slack_integration = result.scalar_one_or_none()

        print("---------------------")
        print(severity_count)
        print("---------------------")

        if not slack_integration:
            return {"message": "No Slack integration found"}

        severity_colors = {
            "critical": ":red_circle:",
            "high": ":large_orange_circle:",
            "medium": ":large_orange_circle:",
            "low": ":large_green_circle:",
            "informational": ":large_blue_circle:",
            "unknown": ":white_circle:"
        }

        message = f"*{sum(severity_count.values())} vulnerabilities found* in *{repo_name}* during *{scan_type}* scan.\n"
        message += "\n".join(
            [f"{severity_colors[severity]} {severity.title()}: {count}"
             for severity, count in severity_count.items() if count > 0]
        )

        query_params = {
            "type": "vulnerability"
        }
        if pr_id:
            query_params['pr_id'] = pr_id
        if commit_id:
            query_params['commit_id'] = commit_id
        if repo_id:
            query_params['repo_id'] = repo_id
        incident_link = (
            f"{FRONTEND_URL}/incidents?{urlencode(query_params)}"
            if query_params
            else f"{FRONTEND_URL}/incidents"
        )

        if pr_id: message += f"\n• Pull Request ID: `{pr_id}`"
        if commit_id: message += f"\n• Commit ID: `{commit_id}`"
        message += f"\n•For more details, click <{incident_link}|here>"

        client = WebClient(token=slack_integration.token)
        response = client.chat_postMessage(
            channel=slack_integration.channel,
            text=message
        )
        return {
            "message": "Notification sent",
            "channel": response["channel"],
            "ts": response["ts"],
            "status": response["ok"]
        }
    except SlackApiError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Slack API error: {e.response['error']}"
        )
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}




async def fetch_and_notify(
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
    pr_id_internal: Optional[int] = None,
):
    try:
        if sec_count == 0 and vul_count == 0:
            return

        print(f"Severity Count: {severity_count}")

        # Fetch Slack integration
        try:
            result = await db.execute(select(SlackIntegration).limit(1))
            slack_integration = result.scalar_one_or_none()
            print("Slack Integration:", slack_integration)
        except Exception as e:
            print(f"Error fetching Slack integration: {e}")
            raise e

        if not slack_integration:
            print("No Slack integration found.")
            return {"message": "No Slack integration found"}

        severity_colors = {
            "critical": ":red_circle:",
            "high": ":large_orange_circle:",
            "medium": ":large_yellow_circle:",
            "low": ":large_green_circle:",
            "informational": ":large_blue_circle:",
            "unknown": ":white_circle:"
        }

        scan_type_label = {
            "pr_scan": "Recent PR Scan",
            "live_commit": "Live Commit Scan",
            "repo_scan": "Repository Scan"
        }.get(scan_type, scan_type)

        try:
            message = f"*Scan Summary for {repo_name} during {scan_type_label}:*\n"
            if sec_count > 0:
                message += f"\n*Secrets Found:* {sec_count}\n"
                secret_items = severity_count.get("secret", [])
                for item in secret_items:
                    if item['count'] > 0:
                        message += f"{severity_colors.get(item['severity'], ':white_circle:')} {item['severity'].title()}: {item['count']}\n"
            if vul_count > 0:
                message += f"\n*Vulnerabilities Found:* {vul_count}\n"
                for severity, count in severity_count.get("vulnerability", {}).items():
                    if count > 0:
                        message += f"{severity_colors[severity]} {severity.title()}: {count}\n"

        except Exception as e:
            print(f"Error constructing message: {e}")
            raise e

        try:
            query_params = {}
            if pr_id:
                query_params['pr_ids'] = pr_id_internal
            if commit_id:
                query_params['commits'] = commit_id
            if repo_id:
                query_params['repo_ids'] = repo_id

            secret_incident_link = f"{FRONTEND_URL}/secret/incidents?{urlencode(query_params)}" if sec_count > 0 else None
            vul_incident_link = f"{FRONTEND_URL}/sca/incidents?{urlencode(query_params)}" if vul_count > 0 else None

            if pr_id:
                message += f"\n• Pull Request ID: `{pr_id}`"
            if commit_id:
                message += f"\n• Commit ID: `{commit_id}`"

            if secret_incident_link:
                message += f"\n• <{secret_incident_link}|Secret Incident Details>"
            if vul_incident_link:
                message += f"\n• <{vul_incident_link}|Vulnerability Incident Details>"

            print("Secret Incident Link:", secret_incident_link)
            print("Vulnerability Incident Link:", vul_incident_link)
            print("Final Message:", message)
        except Exception as e:
            print(f"Error adding incident link: {e}")
            raise e

        # Send notification to Slack
        if sec_count != 0 or vul_count != 0:
            try:
                client = WebClient(token=slack_integration.token)
                response = client.chat_postMessage(
                    channel=slack_integration.channel,
                    text=message
                )
                print("Slack Response:", response)
                return {
                    "message": "Notification sent",
                    "channel": response["channel"],
                    "ts": response["ts"],
                    "status": response["ok"]
                }
            except SlackApiError as e:
                print(f"Slack API error: {e.response['error']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Slack API error: {e.response['error']}"
                )
            except Exception as e:
                print(f"Error sending Slack message: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error: {str(e)}"
                )

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return {"message": f"An error occurred: {str(e)}"}



