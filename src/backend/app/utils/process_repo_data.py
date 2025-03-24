def process_repo_data(repo_data, platform):
    if platform == 'github':
        return {
            'name': repo_data.get('name'),
            'repoUrl': repo_data.get('clone_url'),  # Use clone_url for GitHub
            'author': repo_data.get('owner', {}).get('login'),
            'other_repo_details': repo_data
        }
    elif platform == 'gitlab':
        return {
            'name': repo_data.get('name'),
            # Use http_url_to_repo for GitLab
            'repoUrl': repo_data.get('http_url_to_repo'),
            'author': repo_data.get('namespace', {}).get('name'),
            'other_repo_details': repo_data
        }
    elif platform == 'bitbucket':
        return {
            'name': repo_data.get('name'),
            # Use clone URL for Bitbucket
            'repoUrl': repo_data.get('links', {}).get('clone', [{}])[0].get('href'),
            'author': repo_data.get('owner', {}).get('display_name'),
            'other_repo_details': repo_data
        }
    else:
        raise ValueError('Unsupported platform')
