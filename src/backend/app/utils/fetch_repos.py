import httpx
from typing import List
from app.utils.encoding_base_64 import encode_basic_token


async def fetch_repos(url: str, token: str, git: str) -> List[dict]:
    all_repos = []
    page = 1
    per_page = 25

    headers = {
        "Accept": "application/vnd.github.v3+json",
    }

    if git.lower() == 'bitbucket':
        encoded_token = encode_basic_token(token)
        headers["Authorization"] = f"Basic {encoded_token}"
        headers["Accept"] = "application/json"
    else:
        headers["Authorization"] = f"Bearer {token}"

    print(url, headers)

    print("Fetching for gitlabs")

    async with httpx.AsyncClient() as client:
        while True:
            params = {
                "page": page,
                "per_page": per_page
            }

            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                print(page, data)

                if git.lower() == 'bitbucket':
                    repos = data.get('values', [])
                    if not repos:
                        break
                    all_repos.extend(repos)

                    # Check if there are more pages
                    if len(repos) < data.get('pagelen', per_page):
                        break
                    page += 1
                else:
                    repos = data
                    if not repos:
                        break
                    all_repos.extend(repos)
                    page += 1
                    # GitHub and GitLab APIs return an empty list when there
                    # are no more pages

            else:
                raise Exception(f"Error fetching repos: {response.content}")

    return all_repos
