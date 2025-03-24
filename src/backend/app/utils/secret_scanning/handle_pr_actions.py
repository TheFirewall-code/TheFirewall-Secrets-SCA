from app.utils.secret_scanning.build_headers import build_headers
from dotenv import load_dotenv

load_dotenv()

import requests
import logging
import os
from app.modules.webhookConfig.models.webhookConfig import WebhookConfig

from urllib.parse import urlencode

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def comment_pr(vc_type, access_token, repo, pr_number, sec_count, vul_count, block_message, project_id=None, iid=None, pr_id=None, commit_id=None, repo_id=None, pr_scan_id=None, pr_id_internal=None):
    try:
        # If no issues are found, skip commenting
        if sec_count == 0 and vul_count == 0:
            logger.info(f"No issues found for PR #{pr_number}. Skipping comment.")
            return

        # Building headers
        headers = build_headers(vc_type, access_token)

        # Construct severity text
        severity_text = []
        if sec_count > 0:
            severity_text.append(f"**{sec_count} secrets**")
        if vul_count > 0:
            severity_text.append(f"**{vul_count} vulnerabilities**")

        # Join severity text for display
        severity_summary = " and ".join(severity_text)

        # Construct the incident link
        query_params = {}
        if pr_id:
            query_params['pr_ids'] = pr_id_internal
        if commit_id:
            query_params['commit'] = commit_id
        if repo_id:
            query_params['repo_ids'] = repo_id

        secret_incident_link = f"{FRONTEND_URL}/secret/incidents?{urlencode(query_params)}"
        vul_incident_link = f"{FRONTEND_URL}/sca/incidents?{urlencode(query_params)}"
        print("Generate links for comment", vul_incident_link, secret_incident_link, query_params)

        # Build the PR comment message
        pr_comment = (
            f"### 🚨 [TheFirewall] Scan Results\n\n"
            f"We identified {severity_summary} in this pull request.\n\n"
            f"📋 **Details:**\n"
        )
        if sec_count > 0:
            pr_comment += f"- **Secrets Report:** For a comprehensive report on secrets, click [here]({secret_incident_link}).\n"
        if vul_count > 0:
            pr_comment += f"- **Vulnerabilities Report:** For a detailed report on vulnerabilities, click [here]({vul_incident_link}).\n"
        pr_comment += f"\nYour security matters—take action now!\n\n{block_message}"

        # Determine the correct API URL and data structure based on vc_type
        if vc_type == 'github':
            url = f'https://api.github.com/repos/{repo}/issues/{pr_number}/comments'
            data = {'body': pr_comment}
        elif vc_type == 'bitbucket':
            url = f'https://api.bitbucket.org/2.0/repositories/{repo}/pullrequests/{pr_number}/comments'
            data = {'content': {'raw': pr_comment}}
        elif vc_type == 'gitlab':
            url = f'https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{iid}/notes'
            data = {'body': pr_comment}
        else:
            logger.error("Unsupported version control type: %s", vc_type)
            return

        # Send the POST request to the appropriate API
        logger.info("Posting comment to %s", url)
        response = requests.post(url, headers=headers, json=data)

        # Handle different HTTP response codes
        if response.status_code == 201:
            logger.info('Comment posted successfully to PR #%s', pr_number)
        else:
            logger.error('Failed to post comment to PR #%s. Response: %s', pr_number, response.json())
            response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        # Log any issues with the request (e.g., connection issues, timeouts)
        logger.error("Error posting comment to PR #%s: %s", pr_number, str(e))
    except Exception as e:
        # Log any unexpected errors
        logger.exception("Unexpected error when posting comment to PR #%s", pr_number)






async def update_pr_status(vc_type, access_token, statuses_url, sec_count, vul_count, pr_id=None, repository=None, workspace=None, processing=False, webhook_config: WebhookConfig=None, unblock=False):
    headers = build_headers(vc_type, access_token)

    # Determine the status and description
    if processing:
        state = 'pending'
        description = 'Processing the PR. Please wait...'
    elif unblock:
        state = 'success'
        description = 'PR unblocked because of whitelisting.'
    else:
        block_on_secrets = webhook_config.block_pr_on_sec_found if webhook_config else True
        block_on_vulns = webhook_config.block_pr_on_vul_found if webhook_config else False
        if (sec_count > 0 and block_on_secrets) or (vul_count > 0 and block_on_vulns):
            state = 'failure'
            if sec_count > 0 and vul_count > 0:
                description = f'{sec_count} secrets and {vul_count} vulnerabilities found!'
            elif sec_count > 0:
                description = f'{sec_count} secrets found!'
            else:
                description = f'{vul_count} vulnerabilities found!'
        else:
            state = 'success'
            description = 'No issues detected in the PR.'

    response_status = None
    if vc_type == 'github' and statuses_url:
        payload = {
            'state': state,
            'description': description,
            'context': 'The Firewall',
            'target_url': 'https://secrets.thefirewall.org'
        }
        response_status = requests.post(statuses_url, headers=headers, json=payload)
    
    elif vc_type == 'bitbucket' and pr_id and repository and workspace:
        if state == 'success':
            url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repository}/pullrequests/{pr_id}/approve"
            response_status = requests.post(url, headers=headers)
            print('PR approved successfully.' if response_status.status_code == 200 else 'Failed to approve PR.')
        else:
            url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repository}/pullrequests/{pr_id}/approve"
            response_status = requests.delete(url, headers=headers)
            print('PR disapproved successfully.' if response_status.status_code == 204 else 'Failed to disapprove PR.')
    
    elif vc_type == 'gitlab' and statuses_url:
        payload = {
            'state': 'pending' if state == 'pending' else ('success' if state == 'success' else 'failed'),
            'description': description,
            'context': 'The Firewall'
        }
        response_status = requests.post(statuses_url, headers=headers, json=payload)

    if response_status is not None:
        if response_status.ok:
            print('Operation completed successfully.')
        else:
            print('Operation failed.')
        print('Response Status Code:', response_status.status_code)
        print('Response Content:', response_status.content.decode('utf-8'))