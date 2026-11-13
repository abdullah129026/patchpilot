import os
import stat
import subprocess

import httpx
import pytest

from app.github_client import (
    CloneError,
    IssueFetchError,
    RateLimitedError,
    _dir_size_mb,
    checkout_ref,
    clone_repo,
    fetch_issue,
    fetch_issue_cached,
)


def _git(cwd, *args):
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _local_repo_with_two_commits(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "T")
    (origin / "file.txt").write_text("v1\n")
    _git(origin, "add", "file.txt")
    _git(origin, "commit", "-qm", "v1")
    first = subprocess.run(
        ["git", "-C", str(origin), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (origin / "file.txt").write_text("v2\n")
    _git(origin, "add", "file.txt")
    _git(origin, "commit", "-qm", "v2")
    ws = tmp_path / "ws"
    subprocess.run(
        ["git", "clone", "--depth", "1", "-q", str(origin), str(ws)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert (ws / "file.txt").read_text() == "v2\n"
    return ws, first


def test_checkout_ref_moves_to_older_commit(tmp_path):
    ws, first = _local_repo_with_two_commits(tmp_path)
    checkout_ref(ws, first)
    assert (ws / "file.txt").read_text() == "v1\n"


def test_checkout_ref_rejects_non_sha(tmp_path):
    ws, _ = _local_repo_with_two_commits(tmp_path)
    with pytest.raises(ValueError):
        checkout_ref(ws, "main")
    with pytest.raises(ValueError):
        checkout_ref(ws, "zz" * 20)


def test_checkout_ref_unknown_sha_raises(tmp_path):
    ws, _ = _local_repo_with_two_commits(tmp_path)
    with pytest.raises(CloneError):
        checkout_ref(ws, "0" * 40)


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


def _transport_with_headers(payload, status=200, headers=None):
    def handler(request):
        return httpx.Response(status, json=payload, headers=headers or {})

    return httpx.MockTransport(handler)


def test_fetch_issue_429_is_rate_limited():
    with pytest.raises(RateLimitedError):
        fetch_issue("acme", "demo", 7, transport=_transport({}, status=429))


def test_fetch_issue_403_with_exhausted_quota_is_rate_limited():
    transport = _transport_with_headers(
        {}, status=403, headers={"X-RateLimit-Remaining": "0"}
    )
    with pytest.raises(RateLimitedError):
        fetch_issue("acme", "demo", 7, transport=transport)


def test_fetch_issue_403_without_rate_headers_is_plain_error():
    with pytest.raises(IssueFetchError) as excinfo:
        fetch_issue("acme", "demo", 7, transport=_transport({}, status=403))
    assert not isinstance(excinfo.value, RateLimitedError)
    transport = _transport_with_headers(
        {}, status=403, headers={"X-RateLimit-Remaining": "59"}
    )
    with pytest.raises(IssueFetchError) as excinfo:
        fetch_issue("acme", "demo", 7, transport=transport)
    assert not isinstance(excinfo.value, RateLimitedError)


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


def _fake_git(tmp_path):
    """A git that 'clones' by creating the dest dir (last argument)."""
    script = tmp_path / "git"
    script.write_text(
        '#!/bin/sh\nfor last; do :; done\nmkdir -p "$last"\necho x > "$last/file.txt"\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def test_dir_size_mb_sums_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"x" * 1024)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_bytes(b"y" * 1024)
    assert _dir_size_mb(tmp_path) == pytest.approx(2048 / (1024 * 1024))


def test_clone_over_cap_deletes_workspace_and_raises(tmp_path, monkeypatch):
    # The cap itself is the adversarial behavior: an oversized repo
    # must never reach the runner, and its bytes must not linger.
    # The size is faked (a real 500 MB clone is waste); the measuring
    # function is verified for real in test_dir_size_mb_sums_files.
    from app import config

    _fake_git(tmp_path)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setattr(
        "app.github_client._dir_size_mb", lambda root: config.MAX_CLONE_MB + 1
    )
    dest = tmp_path / "ws"
    with pytest.raises(CloneError, match="exceeds"):
        clone_repo("acme", "demo", dest)
    assert not dest.exists()


def test_clone_under_cap_keeps_workspace(tmp_path, monkeypatch):
    _fake_git(tmp_path)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setattr("app.github_client._dir_size_mb", lambda root: 1)
    dest = tmp_path / "ws"
    clone_repo("acme", "demo", dest)
    assert (dest / "file.txt").exists()
