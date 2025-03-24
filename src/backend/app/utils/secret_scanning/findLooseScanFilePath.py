import requests
import os
from app.utils.secret_scanning.build_headers import build_headers


def fetch_github_files(repo_name, pr_id, source_branch, headers, target_dir):
    api_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_id}/files'
    filename_list = {}

    print(api_url, headers)
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        for file in response.json():
            filename = file['filename']
            full_file_path = os.path.join(target_dir, repo_name, filename)
            file_url = f"https://raw.githubusercontent.com/{repo_name}/{source_branch}/{filename}"
            filename_list[full_file_path] = file_url
    else:
        print(f"Failed to fetch PR details: {response.status_code}")
    return filename_list


def fetch_bitbucket_files(
        repo_name,
        pr_id,
        source_branch,
        headers,
        target_dir,
        commit_hash):
    api_url = f'https://api.bitbucket.org/2.0/repositories/{repo_name}/pullrequests/{pr_id}/diff'
    filename_list = {}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        lines = response.text.splitlines()
        current_file = None

        print("Got lines for bitbucket")
        print(lines)

        for line in lines:
            if line.startswith("diff --git"):
                current_file = line.split()[-1].split("b/")[-1]
            if current_file:
                full_file_path = os.path.join(
                    target_dir, repo_name, current_file)
                file_url = f"https://api.bitbucket.org/2.0/repositories/{repo_name}/src/{commit_hash}/{current_file}"
                filename_list[full_file_path] = file_url
                current_file = None
                print(current_file, file_url)
    else:
        print(f"Error: Received a {response.status_code} status code")
    return filename_list


def fetch_gitlab_files(
        repo_name,
        pr_id,
        source_branch,
        project_id,
        headers,
        target_dir):
    if not project_id:
        raise ValueError("project_id must be provided for GitLab")

    api_url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{pr_id}/changes"
    filename_list = {}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        for change in response.json().get('changes', []):
            filepath = change['new_path']
            full_file_path = os.path.join(target_dir, repo_name, filepath)
            file_url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{filepath}/raw?ref={source_branch}"
            filename_list[full_file_path] = file_url
    else:
        print(
            f"Failed to fetch MR details: {response.status_code} - {response.text}")
    return filename_list


async def find_loose_scan_file_paths(
        vc_type,
        pr_id,
        repo_name,
        source_branch,
        access_token,
        iid=None,
        project_id=None,
        target_dir=None,
        commit_hash=None):
    print("Getting filepaths")
    headers = build_headers(vc_type, access_token)

    if vc_type == 'github':
        filename_list = fetch_github_files(
            repo_name, pr_id, source_branch, headers, target_dir)
    elif vc_type == 'bitbucket':
        filename_list = fetch_bitbucket_files(
            repo_name, pr_id, source_branch, headers, target_dir, commit_hash)
    elif vc_type == 'gitlab':
        filename_list = fetch_gitlab_files(
            repo_name,
            iid,
            source_branch,
            project_id,
            headers,
            target_dir)
    else:
        raise ValueError("Unsupported VCS type")

    if filename_list:
        await get_pr_files(filename_list, headers)
        return filename_list
    else:
        print("No files to download.")
        return []


async def get_pr_files(filename_list, headers):
    print("Downloading files...")
    for target_path, file_url in filename_list.items():
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        print("Downloading", file_url)
        try:
            response = requests.get(file_url, headers=headers)
            response.raise_for_status()
            with open(target_path, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded {target_path}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {file_url}: {e}")
