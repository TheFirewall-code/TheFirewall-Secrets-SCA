from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import logger

from pydantic import ValidationError
from app.modules.pr.schemas.pr_schema import PRCreate
from app.modules.pr.schemas.pr_scan_schema import PRScanCreate, PRScanUpdate
from app.modules.pr.models.pr_scan import StatusEnum, PRScanType
from app.modules.pr.pr_service import create_pr, update_pr_blocked_status, get_pr_blocked_status
from app.modules.pr.pr_scan_service import create_pr_scan, update_pr_scan
from app.modules.repository.repository_service import get_repos_by_vc_id
from app.secret_scanner.pr_secret_scanner import pr_loose_scan, pr_aggressive_scan
from app.utils.secret_scanning.handle_pr_actions import comment_pr, update_pr_status
from app.utils.store_secrets import store_secrets
from app.modules.vulnerability.vulnerability_service import scan_vulnerability_pr_scan_id
from app.modules.jiraAlerts.jiraAlerts_service import send_alert_to_jira
from app.modules.slack_integration.slack_integration_service import fetch_and_notify
from app.modules.webhook.constants import PR_BLOCK_COMMENT, PR_UNBLOCK_COMMENT
from app.modules.webhookConfig.models.webhookConfig import WebhookConfig

async def pr_handler_secret(db: AsyncSession, vc, webhook_config: WebhookConfig, event_info, repo, pr):
    """
    Handles secret scanning for pull requests (PRs).
    Creates a PR scan, performs secret scans, stores results, and updates the PR scan status.
    """
    try:
        repo_id = repo.id
        # Create a PR Scan with initial 'pending' status
        pr_scan_data = PRScanCreate(
            pr_id=pr.id,
            vc_id=vc.id,
            webhook_id=webhook_config.id,
            repo_id=repo_id,
            vc_type=vc.type,
            status=StatusEnum.pending,
            block_status=False,
            other_details=event_info,
            stat_url=event_info['statuses_url'],
            scan_type=PRScanType.SECRET
        )
        pr_scan = await create_pr_scan(db=db, pr_scan_data=pr_scan_data)
        await update_pr_scan(db, pr_scan.id, PRScanUpdate(status=StatusEnum.processing))

        # Perform the appropriate secret scan based on configuration
        secrets = await pr_loose_scan(event_info, vc) if webhook_config.scan_type.value.lower() == "loose" else await pr_aggressive_scan(event_info, vc)

        # Store scan results and categorize by severity

        print("Storing pr secrets")
        print(len(secrets))

        secrets, secrets_new = await store_secrets(
            db=db,
            secrets=secrets,
            repo_id=repo_id,
            scan_type='pr_scan',
            pr_id=pr.id,
            pr_scan_id=pr_scan.id,
            vc_id=vc.id,
            repo_name=event_info['full_reponame'],
            target_dir='/tmp',
            email=event_info['email'],
            author=event_info['author']
        )

        severity_count = {}
        for sec in secrets_new:
            if sec.severity.value.lower() in severity_count:
                severity_count[sec.severity.value.lower()]+=1
            else:
                severity_count[sec.severity.value.lower()]=1

        block_status = False
        if len(secrets) > 0:
            block_status=True

        await update_pr_scan(db, pr_scan.id, PRScanUpdate(status=StatusEnum.completed, block_status=block_status))
        
        return secrets_new, severity_count, pr_scan.id

    except Exception as e:
        logger.error(f"Error in PR secret scan: {e}")
        raise HTTPException(status_code=500, detail="Error in PR secret scan")

async def pr_handler_vulnerability(db: AsyncSession, vc, webhook_config, event_info, repo, pr):
    """
    Handles vulnerability scanning for pull requests.
    Creates a PR scan, performs a vulnerability scan, stores results, and updates the PR scan status.
    """
    try:
        repo_id = repo.id
        # Create a PR Scan with initial 'pending' status
        pr_scan_data = PRScanCreate(
            pr_id=pr.id,
            vc_id=vc.id,
            webhook_id=webhook_config.id,
            repo_id=repo_id,
            vc_type=vc.type,
            status=StatusEnum.pending,
            block_status=False, 
            other_details=event_info,
            stat_url=event_info['statuses_url'],
            scan_type=PRScanType.VULNERABILITY
        )
        pr_scan = await create_pr_scan(db=db, pr_scan_data=pr_scan_data)

        # Perform vulnerability scan and store results
        vulnerabilities, vulnerabilities_new = await scan_vulnerability_pr_scan_id(db, repo.id, pr.id, pr_scan.id, author=event_info["author"])

        # Categorize vulnerabilities by severity
        severity_count = {
            "low": sum(1 for v in vulnerabilities_new if v.severity.lower() == "low"),
            "medium": sum(1 for v in vulnerabilities_new if v.severity.lower() == "medium"),
            "high": sum(1 for v in vulnerabilities_new if v.severity.lower() == "high"),
            "critical": sum(1 for v in vulnerabilities_new if v.severity.lower() == "critical"),
        }

        for vul in vulnerabilities_new:
            print(vul.severity)

        # Update PRScan status to completed
        block_status = False
        if severity_count['high'] > 0 or severity_count['critical'] > 0:
            block_status = True
        await update_pr_scan(db, pr_scan.id, PRScanUpdate(status=StatusEnum.completed, block_status=block_status))

        return vulnerabilities_new, severity_count

    except Exception as e:
        logger.error(f"Error in PR vulnerability scan: {e}")
        raise HTTPException(status_code=500, detail="Error in PR vulnerability scan")

async def pr_handler(db: AsyncSession, vc, webhook_config: WebhookConfig, event_info):
    """
    Main handler for processing pull requests, initiating secret and vulnerability scans, and managing PR status.
    """
    print("into pr handler")
    # Retrieve the repository
    repo = await get_repos_by_vc_id(db, vc.id, repo_name=event_info['repository'])
    if not repo or not repo['data']:
        logger.error("Repository not found")
        raise HTTPException(status_code=404, detail="Repository not found")
    print("Got the repo")

    repo_dict = repo['data'][0]
    repo_id = repo_dict.id

    print(repo_id) 

    # Create a PR entry in the database
    try:
        print("PR link:", event_info['pr_html_url'])
        pr_data = PRCreate(
            pr_id=event_info['pr_id'], 
            pr_name=event_info['repository'],
            repo_id=repo_id,
            pr_link=event_info['pr_html_url'],
            vctype=vc.type,
            vc_id=vc.id,
            webhook_id=webhook_config.id
        )
        pr = await create_pr(db=db, pr=pr_data)

        print(pr)
        print("pr link ", pr.pr_link)

        await update_pr_status(
            vc_type=vc.type.value,
            access_token=vc.token,
            statuses_url=event_info['statuses_url'],
            sec_count=0,
            vul_count=0,
            processing=True
        )

        print("PR status updated")
    except KeyError as ke:
        logger.error(f"Missing key in event_info: {str(ke)}")
        raise HTTPException(status_code=400, detail=f"Missing key: {str(ke)}")
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.json()}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    # Run secret and vulnerability handlers
    secrets, secret_severity_count, pr_scan_id = await pr_handler_secret(db, vc, webhook_config, event_info, repo_dict, pr)
    vulnerabilities, vulnerability_severity_count = await pr_handler_vulnerability(db, vc, webhook_config, event_info, repo_dict, pr)

    # Prepare combined severity data for notifications and updates
    combined_severity_count = {
        "secret": secret_severity_count,
        "vulnerability": vulnerability_severity_count,
    }

    print(combined_severity_count)

    try:
        logger.info("Preparing to post comment and update status to PR...")

        print("block message", webhook_config.block_message)

        await comment_pr(
            vc_type=vc.type.value,
            access_token=vc.token,
            repo=event_info['full_reponame'],
            pr_number=pr.pr_id,
            sec_count=len(secrets),
            vul_count=len(vulnerabilities),
            project_id=event_info.get('project_id'),
            iid=event_info['iid'],
            pr_id=event_info['pr_id'],
            block_message=webhook_config.block_message,
            pr_scan_id=pr_scan_id,
            repo_id=repo_id,
            pr_id_internal=pr.id,
        )

        if vc.type.value is not 'bitbucket':
            await update_pr_status(
                vc_type=vc.type.value,
                access_token=vc.token,
                statuses_url=event_info['statuses_url'],
                sec_count=len(secrets),
                vul_count=len(vulnerabilities),
                processing=False,
                webhook_config=webhook_config
            )
        
        logger.info("Comment successfully posted, PR status Updated")

    except Exception as e:
        logger.error("Error posting comment / updating PR Status: %s", str(e))

    print("-----------------------------------------------------")
    print(combined_severity_count)
    print("-----------------------------------------------------")

    if webhook_config.slack_alerts_enabled:
        await fetch_and_notify(
            db=db,
            severity_count=combined_severity_count,
            sec_count=len(secrets),
            vul_count=len(vulnerabilities),
            repo_name=repo_dict.name,
            scan_type='pr',
            pr_id=event_info['pr_id'],
            commit_id=None,
            repo_id=repo_id,
            pr_scan_id=pr_scan_id,
            pr_id_internal=pr.id,
    )

    if webhook_config.jira_alerts_enabled:
        await send_alert_to_jira(
            db=db,
            severity_count=combined_severity_count,
            sec_count=len(secrets),
            vul_count=len(vulnerabilities),
            repo_name=repo_dict.name,
            scan_type='pr',
            pr_id=event_info['pr_id'],
            repo_id=repo_dict.id,
            pr_scan_id=pr_scan_id,
            pr_id_internal=pr.id,
        )
