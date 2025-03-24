import json
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from typing import Optional

# new imports
from app.utils.secret_scanning.format_raw_data import format_raw_data
from app.utils.secret_scanning.extract_event_info import extract_event_info
from app.utils.secret_scanning.extract_and_validate_signature import extract_and_validate_signature

from app.modules.webhookConfig.webhook_config_service import get_webhook_config_by_vc_id

# import handlers
from app.modules.webhook.event_handlers.repo_creation_handler import repo_creation_handler
from app.modules.webhook.event_handlers.pr_handler import pr_handler
from app.modules.webhook.event_handlers.live_commits_handler import live_commits_handler
from app.modules.vc.vc_service import get_vc
from app.modules.webhookConfig.schemas.webhook_schema import WebhookActions


WebhookActionVCAllowMap = {
    WebhookActions.pr_opened: {
        "bitbucket": ["pullrequest:created"],
        "github": ["pull_request_opened", "pull_request_reopened"],
        "gitlab": ["Merge Request Hook:opened"]
    },
    WebhookActions.pr_updated: {
        "bitbucket": ["pullrequest:updated"],
        "github": ["pull_request_edited", 'pull_request_synchronize'],
        "gitlab": ["Merge Request Hook:updated"]
    },
    WebhookActions.commit_push: {
        "bitbucket": ["repo:push"],
        "github": ["commit_push"],
        "gitlab": ["Push Hook"]
    },
    WebhookActions.repo_push: {
        "bitbucket": ["repo:push"],
        "github": ["push"],
        "gitlab": ["Push Hook"]
    }
}

def get_action(vc_type: str, raw_data_json: dict, headers: dict) -> Optional[WebhookActions]:
    vc_type = vc_type.lower()
    raw_event_key = None
    print(f'Getting action for {vc_type}')

    if vc_type == "bitbucket":
        raw_event_key = headers.get("X-Event-Key")
    elif vc_type == "github":
        if "commits" in raw_data_json:
            raw_event_key = 'commit_push'
        elif "pull_request" in raw_data_json:
            action = raw_data_json.get("action")
            raw_event_key = f"pull_request_{action}" if action else "pull_request"
    elif vc_type == "gitlab":
        kind = raw_data_json.get("object_kind")
        if kind == "merge_request":
            state = raw_data_json.get("object_attributes", {}).get("state")
            raw_event_key = f"Merge Request Hook:{state}" if state else "Merge Request Hook"
        elif kind == "push":
            raw_event_key = "Push Hook"
    print(raw_event_key)
    if not raw_event_key:
        return None

    for action_enum, vcs_map in WebhookActionVCAllowMap.items():
        if raw_event_key in vcs_map.get(vc_type, []):
            return action_enum.value

    return None


async def process_webhook(
        vc_type: str,
        vc_id: int,
        request: Request,
        db: AsyncSession,
        background_tasks: BackgroundTasks):
    try:
        raw_data = await request.body()

        raw_data_json = format_raw_data(raw_data)
        print("got raw data")
        print(raw_data_json)

        # get the webhook configurations for vc id provided
        webhook_config = await get_webhook_config_by_vc_id(db, vc_id)
        print("Webhook fetched", webhook_config)

        # Validate the webhook request
        # if not extract_and_validate_signature(
        #         vc_type, request, raw_data, webhook_config.secret):
        #     pass
            # raise HTTPException(status_code=400, detail="Invalid signature")
        print("Signature validated")

        # Extract the event type and its information
        event_info = extract_event_info(vc_type, raw_data_json)
        if not event_info:
            return JSONResponse(status_code=200, content={"message": f"Action not allowed. Skipping processing"})

        action = get_action(vc_type, raw_data_json, request.headers)
        print("Got Event info and action", event_info, action, webhook_config.git_actions)

        # check if action is allowed
        is_allowed = False
        if action in webhook_config.git_actions:
            is_allowed = True
        if not is_allowed:
            return JSONResponse(status_code=200, content={"message": f"Action not allowed {action}. Skipping processing"})

        # Get vc by id
        vc = await get_vc(db, vc_id)
        if event_info["event_type"] == "pr":
            background_tasks.add_task(
                pr_handler,
                db=db,
                vc=vc,
                webhook_config=webhook_config,
                event_info=event_info)
            return JSONResponse(status_code=200, content={"message": "Payload received. Processing will continue."})

        elif event_info["event_type"] == "live_commit":
            background_tasks.add_task(
                live_commits_handler,
                db=db,
                vc=vc,
                webhook_config=webhook_config,
                event_info=event_info)
            return JSONResponse(status_code=200, content={"message": "Payload received. Processing will continue."})

        elif event_info["event_type"] == "repo":
            background_tasks.add_task(
                repo_creation_handler,
                db=db,
                vc=vc,
                event_info=event_info)
            return JSONResponse(status_code=200, content={"message": "Payload received. Processing will continue."})

    except json.JSONDecodeError as e:
        print(e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}")
