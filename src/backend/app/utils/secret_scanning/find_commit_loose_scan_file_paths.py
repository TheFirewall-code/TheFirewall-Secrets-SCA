import requests
import os
from app.utils.secret_scanning.build_headers import build_headers


async def find_commit_loose_scan_file_paths(
        vc_type,
        target_dir,
        full_reponame,
        ref,
        access_token,
        commit):
    """
    Fetches the diff of the specified commit, extracts added lines, and saves them to a file for scanning.
    """
    repo_folder = os.path.join(target_dir, full_reponame)
    os.makedirs(repo_folder, exist_ok=True)  # Ensure target directory exists

    # Build headers
    headers = build_headers(vc_type, access_token)
    if vc_type == 'bitbucket' and 'Accept' in headers:
        del headers['Accept']

    commit_id = commit['commit_id']
    diff_file_path = os.path.join(repo_folder, f"{commit_id}_changes.txt")

    # Determine URL for fetching the diff
    if vc_type == 'github':
        url = f"https://api.github.com/repos/{full_reponame}/commits/{commit_id}"
    elif vc_type == 'bitbucket':
        url = f"https://api.bitbucket.org/2.0/repositories/{full_reponame}/diff/{commit_id}"
    elif vc_type == 'gitlab':
        url = f"https://gitlab.com/api/v4/projects/{full_reponame.replace('/', '%2F')}/repository/commits/{commit_id}/diff"
    else:
        raise ValueError("Unsupported version control type")

    print(f"Fetching commit diff from: {url}")
    response = requests.get(url, headers=headers)

    print(f"Fetched commit diff: {response.status_code}, Response: {response.text}")
    if response.status_code != 200:
        return []  # Return an empty list on failure

    # Parse and extract added lines from the diff
    if vc_type == 'github':
        # GitHub returns JSON data
        commit_data = response.json()
        added_lines = extract_added_lines_github(commit_data)
    elif vc_type == 'bitbucket':
        # Bitbucket and GitLab return raw diff text
        added_lines = extract_added_lines_raw(response.text)
    else:
        diff_data = response.json()
        if not isinstance(diff_data, list):
            raise ValueError("Expected a list of diff entries.")
        added_lines = extract_added_lines_gitlab(diff_data)

    # Save added lines to a file
    with open(diff_file_path, 'w') as diff_file:
        diff_file.writelines(added_lines)

    print(f"Added lines saved to {diff_file_path} {added_lines}")
    return [diff_file_path]


def extract_added_lines_github(commit_data):
    """
    Extracts lines added in the GitHub commit diff.
    """
    added_lines = []
    files = commit_data.get('files', [])
    for file in files:
        patch = file.get('patch', '')
        added_lines.extend(
            line[1:] + '\n'
            for line in patch.splitlines()
            if line.startswith('+') and not line.startswith('+++')
        )
    return added_lines


def extract_added_lines_raw(diff_text):
    """
    Extract added lines from a raw diff.
    Lines starting with `+` (excluding `+++` which indicates file paths) are considered added lines.
    """
    added_lines = []
    for line in diff_text.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:] + '\n')  # Remove the `+` and preserve the line
    return added_lines


def extract_added_lines_gitlab(diff_data):
    """
    Extract added lines from a list of diff entries (GitLab or Bitbucket style).
    """
    added_lines = []
    for file_diff in diff_data:
        diff = file_diff.get("diff", "")  # Extract the diff as a string
        if not isinstance(diff, str):
            continue  # Skip if diff is not a string

        # Process each line in the diff
        for line in diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:] + '\n')  # Remove the leading `+` and preserve the line
    return added_lines