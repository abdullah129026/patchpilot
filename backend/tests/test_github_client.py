import httpx
import pytest

from app.github_client import (
    IssueFetchError,
    clone_repo,
    fetch_issue,
    fetch_issue_cached,
)


def _transport(payload, status=200):
    def handler(request):
        assert request.url.path == "/repos/acme/demo/issues/7"
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)


def test_fetch_issue_returns_title_and_body():
    issue = fetch_issue(
        "acme", "demo", 7, transport=_transport({"title": "Bug", "body": "boom"})
    )
    assert issue["title"] == "Bug"
    assert issue["body"] == "boom"


def test_fetch_issue_404_raises():
    with pytest.raises(IssueFetchError):
        fetch_issue("acme", "demo", 7, transport=_transport({}, status=404))


def test_cached_issue_is_not_fetched_twice(tmp_path):
    def failing(request):
        raise AssertionError("second fetch must not happen")

    first = fetch_issue_cached(
        tmp_path,
        "job1",
        "acme",
        "demo",
        7,
        transport=_transport({"title": "Bug", "body": "boom"}),
    )
    second = fetch_issue_cached(
        tmp_path, "job1", "acme", "demo", 7, transport=httpx.MockTransport(failing)
    )
    assert first == second == {"title": "Bug", "body": "boom"}
    assert (tmp_path / "job1" / "issue.json").exists()


def test_clone_rejects_bad_names(tmp_path):
    with pytest.raises(ValueError):
        clone_repo("../evil", "demo", tmp_path / "ws")
