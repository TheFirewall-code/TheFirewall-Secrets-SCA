import subprocess
import json
import os

from app.utils.secret_scanning.findLooseScanFilePath import find_loose_scan_file_paths
from app.utils.secret_scanning.fetch_pr_commits import fetch_pr_commits
from app.utils.secret_scanning.create_commit_diff_file import create_commit_diff_file
from app.utils.scan_secrets import scan_secrets

TARGET_DIR = '/tmp'


async def pr_loose_scan(event_info, vc):
    filesPaths = await find_loose_scan_file_paths(
        vc_type=vc.type.value,
        pr_id=event_info['pr_id'],
        repo_name=event_info['full_reponame'],
        access_token=vc.token,
        source_branch=event_info['source_branch'],
        iid=event_info['iid'],
        project_id=event_info['project_id'],
        target_dir=TARGET_DIR,
        commit_hash=event_info.get('commit_hash', None)
    )

    secrets = scan_secrets(filesPaths)
    return secrets


async def pr_aggressive_scan(event_info, vc):
    commitsList = await fetch_pr_commits(vc_type=vc.type.value, repository=event_info['full_reponame'], pr_id=event_info['pr_id'], access_token=vc.token)

    files_list = []
    for commit_sha in commitsList:
        full_filename = os.path.join(
            TARGET_DIR, event_info['full_reponame'], commit_sha)
        file = create_commit_diff_file(
            vc_type=vc.type.value,
            repo_name=event_info['full_reponame'],
            project_id=event_info['project_id'],
            access_token=vc.token,
            commit_sha=commit_sha,
            full_filename=full_filename
        )
        if isinstance(file, list):
            files_list.extend(file)
        else:
            files_list.append(file)

    secrets = scan_secrets(files_list)
    return secrets
