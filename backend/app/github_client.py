"""GitHub ingest (Phase 3): issue fetch once per job, cached, plus clone.

The API token, when set, comes only from the PATCHPILOT_GITHUB_TOKEN
environment variable and is never logged. Clone uses an argument
list, never a shell, and owner/repo names are validated before they
reach git. A clone bigger than the Phase 0 cap is deleted, not run.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import httpx

from app import config
from app.github_url import _OWNER_REPO

_REF = re.compile(r"^[0-9a-f]{40}$")

_API = "https://api.github.com"


class IssueFetchError(Exception):
    pass


class CloneError(Exception):
    pass


def fetch_issue(owner, repo, number, token=None, transport=None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "patchpilot-agent",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(transport=transport, timeout=30) as client:
            resp = client.get(
                f"{_API}/repos/{owner}/{repo}/issues/{number}", headers=headers
            )
    except httpx.HTTPError as exc:
        raise IssueFetchError(f"GitHub request failed: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise IssueFetchError(f"GitHub returned {resp.status_code} for the issue")
    data = resp.json()
    return {"title": data.get("title", ""), "body": data.get("body") or ""}


def fetch_issue_cached(store_dir, job_id, owner, repo, number, **kwargs) -> dict:
    path = Path(store_dir) / job_id / "issue.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except ValueError:
            pass
    issue = fetch_issue(owner, repo, number, **kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(issue))
    return issue


def _dir_size_mb(root: Path) -> float:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total / (1024 * 1024)


def clone_repo(owner, repo, dest, timeout=600) -> None:
    if not _OWNER_REPO.match(owner) or not _OWNER_REPO.match(repo):
        raise ValueError(f"invalid owner or repo name: {owner}/{repo}")
    dest = Path(dest)
    if dest.exists():
        raise CloneError("workspace already exists")
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                f"https://github.com/{owner}/{repo}.git",
                str(dest),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise CloneError("git clone failed") from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError("git clone timed out") from exc
    if _dir_size_mb(dest) > config.MAX_CLONE_MB:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(f"repo exceeds the {config.MAX_CLONE_MB} MB clone cap")


def checkout_ref(workspace, ref: str) -> None:
    """Move a clone to one recorded commit (fixture jobs only).

    The fixture suite reproduces historical bugs, so it runs the repo
    at the commit just before the fix, not at HEAD. GitHub serves a
    fetch by full SHA, so a depth-1 clone plus this one fetch is all
    it takes. Only a full SHA is accepted: a branch or tag name here
    would let a caller aim the runner at arbitrary code.
    """
    if not _REF.match(ref or ""):
        raise ValueError(f"invalid ref: {ref!r}")
    workspace = Path(workspace)
    try:
        subprocess.run(
            ["git", "-C", str(workspace), "fetch", "--depth", "1", "origin", ref],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(workspace), "checkout", "--quiet", ref],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise CloneError("repo checkout failed") from exc
    except subprocess.TimeoutExpired as exc:
        raise CloneError("repo checkout timed out") from exc
