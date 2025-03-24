import subprocess
import os
from datetime import datetime

from dill.logger import stderr_handler

from app.utils.delete_folder import delete_folder
from app.core.logger import logger

def clone_repo(
        vc_type: str,
        clone_url: str,
        token: str,
        repo_name: str,
        branch_name: str = None) -> str:
    # Define the target directory
    target_dir = f"tmp/{vc_type}/"
    target_repo = f"{target_dir}{repo_name}"

    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True, mode=0o777)

    if os.path.exists(target_repo):
        logger.info(
            f"Repository {repo_name} already exists. Pulling the latest changes.")
        delete_folder(target_repo)

    logger.info(f"Cloning repository {repo_name}.")
    # Handle cloning for different version control systems
    if vc_type.lower() == 'bitbucket':
        at_index = clone_url.index('@')
        auth_clone_url = f"https://{token}{clone_url[at_index:]}"
    elif vc_type.lower() == 'gitlab':
        auth_clone_url = f"https://oauth2:{token}@{clone_url[8:]}"
    else:
        auth_clone_url = f"https://{token}:x-oauth-basic@{clone_url[8:]}"

    command = ["git", "clone", auth_clone_url]
    if branch_name:
        command = ["git", "clone", "--branch", branch_name, auth_clone_url]
    print("Cloning command", command)
    response = subprocess.Popen(
        command,
        cwd=target_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True)
    response.communicate()

    return target_repo

def get_branches_from_commit(repo_path: str, commit_hash: str) -> list:
    """
    Get the branches that contain a specific commit.

    Args:
        repo_path (str): The path to the cloned repository.
        commit_hash (str): The commit hash to search for in the branches.

    Returns:
        list: A list of branch names that contain the commit.
    """
    try:
        # Navigate to the repository directory
        os.chdir(repo_path)

        # Run the git command to find branches containing the commit
        result = subprocess.run(
            ["git", "branch", "--contains", commit_hash],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check if the command was successful
        if result.returncode != 0:
            logger.error(
                f"Failed to get branches for commit {commit_hash}: {result.stderr}"
            )
            return []

        # Parse the output to get the branch names
        branches = [line.strip()
                    for line in result.stdout.splitlines() if line.strip()]
        return branches

    except Exception as e:
        logger.error(f"An error occurred while getting branches: {e}")
        return []
