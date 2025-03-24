from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.modules.live_commits.live_commits_scans_service import add_live_commit_scan, update_live_commit_scan_status
from app.modules.live_commits.models.live_commits_scan import LiveCommitScanType
from app.modules.live_commits.schemas.live_commits_schemas import LiveCommitScanCreate, StatusEnum
from app.modules.repository.repository_service import get_repos_by_vc_id
from app.modules.vulnerability.vulnerability_service import scan_vulnerability_live_commit_id
from app.secret_scanner.live_commits_secret_scanner import commit_loose_scan, commit_aggressive_scan
from app.modules.live_commits.live_commits_service import add_live_commit
from app.modules.live_commits.schemas.live_commits_schemas import LiveCommitCreate
from app.utils.store_secrets import store_secrets
from app.modules.jiraAlerts.jiraAlerts_service import send_alert_to_jira
from app.modules.slack_integration.slack_integration_service import fetch_and_notify

SCAN_COUNT = 0

async def live_commits_handler_secrets(db: AsyncSession, vc, repo, live_commit, commit, webhook_config, event_info):
    global SCAN_COUNT
    try:
        # Creating a scan
        print("Creating a live commit scan Here")
        print(SCAN_COUNT)
        SCAN_COUNT=SCAN_COUNT+1
        live_commit_scan_data = LiveCommitScanCreate(
            vc_id=vc.id,
            webhook_id=webhook_config.id,
            repo_id=repo.id,
            status=StatusEnum.pending,
            scan_type=LiveCommitScanType.SECRET,
            live_commit_id=live_commit.id
        )
        live_commit_scan = await add_live_commit_scan(db=db, live_commit_scan=live_commit_scan_data)

        # Scanning
        if webhook_config.scan_type.value.lower() == "loose":
            secrets = await commit_loose_scan(event_info, vc, commit)
        else:
            secrets = await commit_aggressive_scan(event_info, vc, commit)

        secrets, secrets_new = await store_secrets(
            db=db,
            secrets=secrets,
            repo_id=repo.id,
            scan_type='live_commit',
            live_commit_id=live_commit.id,
            vc_id=vc.id,
            commit=commit["commit_id"],
            live_commit_scan_id=live_commit_scan.id,
            email=event_info['email'],
            author=event_info['author']
        )
        print("Secrets stored in live commit scan", len(secrets), " New secrets", len(secrets_new))
        severity_count = {}
        for sec in secrets_new:
            if sec.severity.value.lower() in severity_count:
                severity_count[sec.severity.value.lower()]+=1
            else:
                severity_count[sec.severity.value.lower()]=1

        # Mark scan as completed
        await update_live_commit_scan_status(db, live_commit_scan.id, StatusEnum.completed)
        print("Updated live commit scan")
        print("returning secrets")
        return secrets_new, severity_count

    except Exception as e:
        logger.error(f"Error during secrets scan for commit {commit['commit_id']} in repo {repo.name}: {e}")
        await update_live_commit_scan_status(db, live_commit_scan.id, StatusEnum.failed)
        return []

async def live_commits_handler_vulnerability(db: AsyncSession, vc, repo, live_commit, commit, webhook_config, event_info):
    try:
        print('Live commit scan for vulnerability')
        # Create a scan
        live_commit_scan_data = LiveCommitScanCreate(
            vc_id=vc.id,
            webhook_id=webhook_config.id,
            repo_id=repo.id,
            status=StatusEnum.pending,
            scan_type=LiveCommitScanType.VULNERABILITY,
            live_commit_id=live_commit.id
        )

        live_commit_scan = await add_live_commit_scan(db=db, live_commit_scan=live_commit_scan_data)

        print('Added Live commit scan for vulnerability')

        # Run scan
        vulnerabilities, vulnerabilities_new = await scan_vulnerability_live_commit_id(
            db, repo.id, live_commit.id, live_commit_scan.id, commit["commit_id"], commit["author_name"]
        )
        await update_live_commit_scan_status(db, live_commit_scan.id, StatusEnum.completed)
        print('Updated Live commit scan for vulnerability')

        # Categorize vulnerabilities by severity
        severity_count = {
            "low": sum(1 for v in vulnerabilities_new if v.severity.lower() == "low"),
            "medium": sum(1 for v in vulnerabilities_new if v.severity.lower() == "medium"),
            "high": sum(1 for v in vulnerabilities_new if v.severity.lower() == "high"),
            "critical": sum(1 for v in vulnerabilities_new if v.severity.lower() == "critical"),
        }

        for vul in vulnerabilities_new:
            print(vul.severity)

        return vulnerabilities_new, severity_count

    except Exception as e:
        logger.error(f"Error during vulnerability scan for commit {commit['commit_id']} in repo {repo.name}: {e}")
        await update_live_commit_scan_status(db, live_commit_scan.id, StatusEnum.failed)
        return [], {}

async def live_commits_handler(
        db: AsyncSession,
        vc,
        webhook_config,
        event_info
    ):

    try:
        repo = await get_repos_by_vc_id(db, vc.id, repo_name=event_info['repository'])
        if not repo or not repo['data']:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_dict = repo['data'][0]
        repo_id = repo_dict.id
        print("Got the repo")

        all_secrets = []
        all_vulnerabilities = []

        print("Length of the commit array:", len(event_info['commits']))

        # Process each commit in the event info
        for commit_data in event_info['commits']:
            if vc.type.value in ['github', 'gitlab']:
                commit = {
                    'commit_id': commit_data['id'],
                    'commit_url': commit_data.get('url', ''),
                    'author_name': commit_data.get('author', {}).get('name', 'Unknown'),
                    'commit_msg': commit_data.get('message', '')
                }
                
            elif vc.type.value == 'bitbucket':
                commit = {
                    'commit_id': commit_data['hash'],
                    'commit_url': commit_data['links'].get('html', {}).get('href', ''),
                    'author_name': commit_data.get('author', {}).get('user', {}).get('display_name', 'Unknown'),
                    'commit_msg': commit_data.get('message', '')
                }
            print("Scanning commit")
            print(commit)
        

            print("Creating Just Live Commit")

            live_commit_data = LiveCommitCreate(
                vc_id=vc.id,
                repo_id=repo_id,
                branch=event_info['branch_name'],
                commit_id=commit['commit_id'],
                commit_url=commit['commit_url'],
                author_name=commit['author_name'],
                commit_msg=commit['commit_msg'],
                other_details=commit,
            )

            # Add live commit to the database
            live_commit = await add_live_commit(db=db, live_commit=live_commit_data)

            # Handle secrets
            secrets, secret_severity_count = await live_commits_handler_secrets(
                db, vc, repo_dict, live_commit, commit, webhook_config, event_info
            )
            all_secrets.extend(secrets)

            # Handle vulnerabilities
            vulnerabilities = await live_commits_handler_vulnerability(
                db, vc, repo_dict, live_commit, commit, webhook_config, event_info
            )

            combined_severity_count = {
                "secret": secret_severity_count,
                "vulnerability": len(vulnerabilities),
            }

            print("-------------------------------------------------")
            print(combined_severity_count)
            print("-------------------------------------------------")

            # Integrations: Slack and JIRA alerts
            try:
                if webhook_config.slack_alerts_enabled:
                    print("Sending slack messages")
                    await fetch_and_notify(
                        db=db,
                        severity_count=combined_severity_count,
                        sec_count=len(secrets),
                        vul_count=len(vulnerabilities),
                        repo_name=repo_dict.name,
                        scan_type="live_commit",
                        pr_id=None,
                        commit_id=commit['commit_id'],
                        repo_id=repo_id,

                    )

                if webhook_config.jira_alerts_enabled:
                    await send_alert_to_jira(
                        db=db,
                        severity_count=combined_severity_count,
                        sec_count=len(secrets),
                        vul_count=len(vulnerabilities),
                        repo_name=repo_dict.name,
                        scan_type="live_commit",
                        pr_id=None,
                        commit_id=commit['commit_id'],
                        repo_id=repo_dict.id,
                    )

            except Exception as e:
                logger.error(f"Error in sending alerts for repository {repo_dict.name}: {str(e)}")

        return True

    except HTTPException as e:
        logger.error(f"Handler error: {e.detail}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error in live commits handler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
