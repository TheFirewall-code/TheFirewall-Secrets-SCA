import os
import requests
from app.utils.secret_scanning.build_headers import build_headers


def create_commit_diff_file(
        vc_type,
        access_token,
        repo_name,
        commit_sha,
        full_filename,
        project_id=None):
    if vc_type == 'github':
        url = f"https://api.github.com/repos/{repo_name}/commits/{commit_sha}"
    elif vc_type == 'bitbucket':
        url = f"https://api.bitbucket.org/2.0/repositories/{repo_name}/diff/{commit_sha}"
    elif vc_type == 'gitlab':
        project_id = project_id
        url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits/{commit_sha}/diff"
    else:
        print(f"Unknown version control type: {vc_type}")
        return []

    headers = build_headers(vc_type, access_token)
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(
            f"Failed to fetch commit {commit_sha}: {response.status_code} - {response.text}")
        return []

    file_list = []
    if vc_type == 'github':
        commit_data = response.json()
        for file in commit_data.get('files', []):
            file_basename = os.path.basename(file['filename'])
            temp_file = f"{full_filename}_{file_basename}"
            file_list.append(temp_file)

            with open(temp_file, "w") as f:
                if 'patch' in file:
                    for line in file['patch'].split('\n'):
                        if line.startswith('+') and not line.startswith('+++'):
                            f.write(line[1:] + "\n")

    elif vc_type == 'bitbucket':
        commit_data = response.text.split('diff --git')
        for file_data in commit_data[1:]:
            file_lines = file_data.split('\n')
            file_path = file_lines[0].split(' ')[1]
            temp_file = f"{full_filename}_{file_path.replace('/', '_')}"
            file_list.append(temp_file)

            with open(temp_file, "w") as f:
                for line in file_lines:
                    if line.startswith('+') and not line.startswith('+++'):
                        f.write(line[1:] + "\n")

    elif vc_type == 'gitlab':
        commit_data = response.json()
        for file in commit_data:
            temp_file = f"{full_filename}_{file['new_path']}"
            file_list.append(temp_file)

            with open(temp_file, "w") as f:
                for line in file['diff'].split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        f.write(line[1:] + "\n")

    return file_list
