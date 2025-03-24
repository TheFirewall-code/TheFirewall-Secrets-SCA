from fastapi import HTTPException
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def extract_event_info(vc_type: str, raw_data_json: dict):
    """
    Extract repository and event information from webhook data based on event type.

    Parameters:
    - vc_type (str): Version control type, e.g., 'github', 'gitlab', 'bitbucket'.
    - raw_data_json (dict): Webhook payload data in JSON format.

    Returns:
    - Dictionary containing extracted event details and event type.
    """
    print(f"Getting event infor for {vc_type}")
    try:
        # Pull request / Merge request event
        if "pull_request" in raw_data_json or "pullrequest" in raw_data_json or raw_data_json.get("object_kind") == "merge_request":
            event_type = "pr"
            print('Checking for pr')

            if vc_type == "github":
                required_keys = ['pull_request', 'repository', 'sender']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "pr_id": raw_data_json['pull_request']["number"],
                    "pr_no": raw_data_json['pull_request']["number"],
                    "repository": raw_data_json['repository']["name"],
                    "source_branch": raw_data_json['pull_request']['head']['ref'],
                    "destination_branch": raw_data_json['pull_request']['base']['ref'],
                    "full_reponame": raw_data_json['repository']["full_name"],
                    "clone_url": raw_data_json['repository']["clone_url"],
                    "pr_link": raw_data_json['pull_request']["html_url"],
                    "pr_html_url": raw_data_json['pull_request']["html_url"],
                    "statuses_url": raw_data_json['pull_request']['head']["repo"]["statuses_url"][:-6] + "/" + raw_data_json['pull_request']['head']["sha"],
                    "author": raw_data_json['sender']['login'],
                    "email": raw_data_json['pull_request']['user'].get('url', None),  # Adding email
                    "iid": None,
                    "project_id": None,
                    "commit": raw_data_json["pull_request"]
                }
            elif vc_type == "gitlab":
                required_keys = ['project', 'object_attributes', 'user']
                validate_keys(required_keys, raw_data_json, vc_type)

                project_id = raw_data_json['project']['id']
                return {
                    "event_type": event_type,
                    "pr_id": raw_data_json['object_attributes']["id"],
                    "project_id": project_id,
                    "repository": raw_data_json['project']['name'],
                    "pr_no": raw_data_json['object_attributes']['iid'],
                    "source_branch": raw_data_json['object_attributes']['source_branch'],
                    "destination_branch": raw_data_json['object_attributes']['target_branch'],
                    "full_reponame": raw_data_json['project']["path_with_namespace"],
                    "clone_url": raw_data_json['project']["git_http_url"],
                    "pr_link": raw_data_json['object_attributes']["url"],
                    "pr_html_url": raw_data_json['object_attributes']["url"],
                    "iid": raw_data_json['object_attributes']['iid'],
                    "statuses_url": f"https://gitlab.com/api/v4/projects/{project_id}/statuses/{raw_data_json['object_attributes']['last_commit']['id']}",
                    "author": raw_data_json['user']['username'],
                    "email": raw_data_json['user'].get('email', None)  # Adding email
                }
            elif vc_type == "bitbucket":
                required_keys = ['pullrequest', 'repository', 'actor']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "pr_id": raw_data_json['pullrequest']["id"],
                    "pr_no": raw_data_json['pullrequest']["id"],
                    "repository": raw_data_json['repository']["name"],
                    "source_branch": raw_data_json['pullrequest']['source']['branch']['name'],
                    "destination_branch": raw_data_json['pullrequest']['destination']['branch']['name'],
                    "full_reponame": raw_data_json['repository']["full_name"],
                    "clone_url": raw_data_json['repository']["links"]['html']["href"],
                    "pr_link": raw_data_json['pullrequest']["links"]["html"]["href"],
                    "pr_html_url": raw_data_json['pullrequest']["links"]["html"]["href"],
                    "statuses_url": raw_data_json['pullrequest']["links"]["statuses"]["href"],
                    "author": raw_data_json['actor']['nickname'],
                    "email": raw_data_json['pullrequest']['author']['links']['html'].get('href', None),  # Adding email
                    "iid": None,
                    "project_id": None,
                    "commit_hash": raw_data_json['pullrequest']['source']['commit']['hash']
                }

        # Push event
        elif "commits" in raw_data_json or "push" in raw_data_json or raw_data_json.get("object_kind") == "push":
            event_type = "live_commit"
            branch_name = raw_data_json['ref'].split('/')[-1] if vc_type in ["github", "gitlab"] else raw_data_json['push']['changes'][0]['new']['name']
            print('Checking for live_commit')

            if vc_type == "github":
                required_keys = ['repository', 'ref', 'commits', 'sender']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "repository": raw_data_json['repository']["name"],
                    "ref": raw_data_json['ref'],
                    "full_reponame": raw_data_json['repository']["full_name"],
                    "clone_url": raw_data_json['repository']["clone_url"],
                    "commits": raw_data_json['commits'],
                    "source_branch": raw_data_json['ref'],
                    "author": raw_data_json['sender']['login'],
                    "email": raw_data_json['commits'][0]['author'].get('url', None),  # Adding email
                    "branch_name": branch_name,
                    "project_id": None
                }
            elif vc_type == "gitlab":
                required_keys = ['project', 'ref', 'commits', 'user_name']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "repository": raw_data_json['project']["name"],
                    "project_id": raw_data_json['project']["id"],
                    "ref": raw_data_json['ref'],
                    "full_reponame": raw_data_json['project']["path_with_namespace"],
                    "clone_url": raw_data_json['project']["git_http_url"],
                    "commits": raw_data_json['commits'],
                    "source_branch": raw_data_json['ref'],
                    "author": raw_data_json['user_name'],
                    "email": raw_data_json['commits'][0]['author'].get('email', None),  # Adding email
                    "branch_name": branch_name,
                }
            elif vc_type == "bitbucket":
                required_keys = ['repository', 'push']
                validate_keys(required_keys, raw_data_json, vc_type)

                changes = raw_data_json.get('push', {}).get('changes', [])
                if not changes or 'commits' not in changes[0]:
                    raise KeyError(f"{vc_type}: Missing key 'commits' in payload")

                commits = changes[0]['commits']
                branch_name = changes[0]['new']['name']

                return {
                    "event_type": event_type,
                    "repository": raw_data_json['repository']["name"],
                    "ref": branch_name,
                    "full_reponame": raw_data_json['repository']["full_name"],
                    "clone_url": raw_data_json['repository']["links"]['self']['href'],
                    "commits": commits,
                    "source_branch": branch_name,
                    "author": changes[0]['new']['target']['author']['user']['display_name'],
                    "email": changes[0]['new']['target']['author']['raw'],  # Adding email
                    "branch_name": branch_name,
                    "project_id": raw_data_json['repository']["owner"]['uuid']
                }

        # Repository creation event
        elif raw_data_json.get("action") == "created" or raw_data_json.get("object_kind") == "project_create":
            event_type = "repo"

            if vc_type == "github":
                required_keys = ['repository', 'sender']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "repo_name": raw_data_json['repository']['name'],
                    "clone_url": raw_data_json['repository']['clone_url'],
                    "author": raw_data_json['sender']['login'],
                    "email": raw_data_json['repository']['owner'].get('email', None),  # Adding email
                    "other_details": raw_data_json['repository']
                }
            elif vc_type == "gitlab":
                required_keys = ['project', 'owner_name']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "repo_name": raw_data_json['project']['name'],
                    "clone_url": raw_data_json['project']['git_http_url'],
                    "author": raw_data_json['owner_name'],
                    "email": raw_data_json['project'].get('owner_email', None),  # Adding email
                    "other_details": raw_data_json['project']
                }
            elif vc_type == "bitbucket":
                required_keys = ['repository']
                validate_keys(required_keys, raw_data_json, vc_type)

                return {
                    "event_type": event_type,
                    "repo_name": raw_data_json['repository']['name'],
                    "clone_url": raw_data_json['repository']['links']['html']['href'],
                    "author": raw_data_json['repository']['owner']['nickname'],
                    "email": raw_data_json['repository']['owner'].get('email', None),  # Adding email
                    "other_details": raw_data_json['repository']
                }

        # Unsupported event type
        # raise HTTPException(status_code=400, detail="Unsupported event type")
        return None

    except KeyError as e:
        logger.error(f"Missing key: {e}")
        raise HTTPException(status_code=400, detail=f"Missing required key: {e}")


def validate_keys(required_keys, payload, vc_type):
    """Validate if required keys exist in the payload."""
    for key in required_keys:
        if key not in payload:
            raise KeyError(f"{vc_type}: Missing required key '{key}'")
