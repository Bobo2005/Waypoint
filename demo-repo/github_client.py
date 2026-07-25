"""Minimal client for listing a GitHub user's public repos."""
from typing import Optional

import httpx

DEFAULT_TIMEOUT = 5


def list_repos(username: str, base_url: str, token: Optional[str] = None) -> list:
    """Return the list of repos for `username`.

    Raises httpx.HTTPStatusError if the server responds with a non-2xx status.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = httpx.get(
        f"{base_url}/users/{username}/repos",
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
