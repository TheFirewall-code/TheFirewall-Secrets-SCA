import subprocess
import json
import os

from app.utils.secret_scanning.findLooseScanFilePath import find_loose_scan_file_paths
from app.utils.secret_scanning.fetch_pr_commits import fetch_pr_commits
from app.utils.secret_scanning.create_commit_diff_file import create_commit_diff_file
from app.utils.scan_secrets import scan_secrets
from app.utils.secret_scanning.find_commit_loose_scan_file_paths import find_commit_loose_scan_file_paths

TARGET_DIR = '/tmp'


async def commit_loose_scan(event_info, vc, commit):
    filesPaths = await find_commit_loose_scan_file_paths(
        vc_type=vc.type.value,
        target_dir=TARGET_DIR,
        full_reponame=event_info['full_reponame'],
        ref=event_info['ref'],
        access_token=vc.token,
        commit=commit
    )

    print(filesPaths)

    secrets = scan_secrets(filesPaths)
    return secrets


async def commit_aggressive_scan(event_info, vc, commit):

    files_list = []
    full_filename = os.path.join(
        TARGET_DIR,
        event_info['full_reponame'],
        commit['commit_id'])

    files = create_commit_diff_file(
        vc_type=vc.type.value,
        repo_name=event_info['full_reponame'],
        project_id=event_info['project_id'],
        access_token=vc.token,
        commit_sha=commit['commit_id'],
        full_filename=full_filename
    )
    if isinstance(files, list):
        files_list.extend(files)
    else:
        files_list.append(files)

    secrets = scan_secrets(files_list)
    return secrets
