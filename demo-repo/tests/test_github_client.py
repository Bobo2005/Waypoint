from github_client import list_repos


def test_list_repos_returns_list(live_server):
    repos = list_repos("octocat", base_url=live_server)
    assert isinstance(repos, list)
    assert repos[0]["name"] == "demo-repo"


def test_list_repos_with_token(live_server):
    repos = list_repos("octocat", base_url=live_server, token="fake-token")
    assert repos[0]["stars"] == 3