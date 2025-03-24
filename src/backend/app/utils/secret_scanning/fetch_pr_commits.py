import requests
from app.utils.secret_scanning.build_headers import build_headers


async def fetch_pr_commits(vc_type, repository, pr_id, access_token):

    # Determine API URL based on platform
    if vc_type == 'github':
        url = f"https://api.github.com/repos/{repository}/pulls/{pr_id}/commits"
    elif vc_type == 'gitlab':
        url = f"https://gitlab.com/api/v4/projects/{repository}/merge_requests/{pr_id}/commits"
    elif vc_type == 'bitbucket':
        url = f"https://api.bitbucket.org/2.0/repositories/{repository}/pullrequests/{pr_id}/commits"
    else:
        raise ValueError(
            "Unsupported version control type. Choose 'github', 'gitlab', or 'bitbucket'.")

    headers = build_headers(vc_type, access_token)
    response = requests.get(url, headers=headers)

    commits_list = []
    if response.status_code == 200:
        commits = response.json()
        for commit in commits if vc_type != 'bitbucket' else commits['values']:
            commit_sha = commit['id'] if vc_type == 'gitlab' else commit['sha'] if vc_type == 'github' else commit['hash']
            commits_list.append(commit_sha)
        print("Commits found")

    else:
        print(
            f"Failed to fetch commits: {response.status_code} - {response.text}")

    return commits_list
