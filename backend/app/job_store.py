"""Filesystem job store (Phase 0, ADR-005).

One directory per job holding report.json. No database in v1: deleting
a job is deleting a directory, which is also the takedown story.
Job ids are server-generated, so a caller can never pick a path.
"""

import json
import re
import secrets
from pathlib import Path

from app.github_url import _OWNER_REPO

_ID = re.compile(r"^[a-z0-9]{12}$")


def _safe_name(value: str) -> None:
    if not _OWNER_REPO.match(value):
        raise ValueError(f"invalid name: {value!r}")


def create_job(store_dir: str | Path, owner: str, repo: str, number: int) -> dict:
    _safe_name(owner)
    _safe_name(repo)
    job_id = secrets.token_hex(6)
    job = {
        "id": job_id,
        "status": "queued",
        "verdict": None,
        "fixture": False,
        "issue": {"owner": owner, "repo": repo, "number": number},
        "attempts": [],
    }
    path = Path(store_dir) / job_id
    path.mkdir(parents=True, exist_ok=False)
    (path / "report.json").write_text(json.dumps(job, indent=2))
    return job


def get_job(store_dir: str | Path, job_id: str) -> dict | None:
    if not _ID.match(job_id or ""):
        return None
    path = Path(store_dir) / job_id / "report.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None
