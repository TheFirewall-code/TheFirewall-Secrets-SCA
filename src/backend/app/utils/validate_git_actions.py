from typing import List

# Define the allowed Git actions for different vc_types
GIT_ACTIONS = {
    "github": [
        "opened", "closed", "merged", "reopened", "edited", "synchronize"
    ],
    "gitlab": [
        "open", "close", "merge", "reopen", "update"
    ],
    "bitbucket": [
        "opened", "declined", "merged", "reopened", "updated"
    ]
}


def validate_git_actions(vc_type: str, git_actions: List[str]) -> bool:
    """
    Validate git actions against the allowed actions for the specified vc_type.

    :param vc_type: The version control type (e.g., GitHub, GitLab, Bitbucket)
    :param git_actions: List of git actions to validate
    :return: True if all actions are valid, False otherwise
    """
    allowed_actions = GIT_ACTIONS.get(vc_type, [])
    return all(action in allowed_actions for action in git_actions)
