"""Filesystem job store (Phase 0, ADR-005).

One directory per job holding report.json. No database in v1: deleting
a job is deleting a directory, which is also the takedown story.
Job ids are server-generated, so a caller can never pick a path.

Phase 2 adds the submitter's delete token: created with the job,
returned exactly once, and stored only as a hash. Anyone else who
wants a report removed uses the takedown-request path, which records
the request for the founder instead of deleting on an anonymous say-so.
"""

import hashlib
import hmac
import json
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.github_url import _OWNER_REPO

_ID = re.compile(r"^[a-z0-9]{12}$")
_ACTIVE = {"queued", "running"}


def _safe_name(value: str) -> None:
    if not _OWNER_REPO.match(value):
        raise ValueError(f"invalid name: {value!r}")


def _read_raw(store_dir: str | Path, job_id: str) -> dict | None:
    if not _ID.match(job_id or ""):
        return None
    path = Path(store_dir) / job_id / "report.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _public(job: dict) -> dict:
    return {k: v for k, v in job.items() if k != "delete_token_hash"}


def count_active_jobs(store_dir: str | Path) -> int:
    root = Path(store_dir)
    if not root.is_dir():
        return 0
    count = 0
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            job = json.loads((child / "report.json").read_text())
        except (OSError, ValueError):
            continue
        if job.get("status") in _ACTIVE:
            count += 1
    return count


def create_job(
    store_dir: str | Path, owner: str, repo: str, number: int, ref: str | None = None
) -> dict:
    _safe_name(owner)
    _safe_name(repo)
    if ref is not None and not re.match(r"^[0-9a-f]{40}$", ref):
        raise ValueError(f"invalid ref: {ref!r}")
    job_id = secrets.token_hex(6)
    token = secrets.token_hex(16)
    issue = {"owner": owner, "repo": repo, "number": number}
    if ref is not None:
        issue["ref"] = ref
    stored = {
        "id": job_id,
        "status": "queued",
        "verdict": None,
        "fixture": False,
        "issue": issue,
        "attempts": [],
        "queue_position": count_active_jobs(store_dir) + 1,
        "delete_token_hash": hashlib.sha256(token.encode()).hexdigest(),
    }
    path = Path(store_dir) / job_id
    path.mkdir(parents=True, exist_ok=False)
    (path / "report.json").write_text(json.dumps(stored, indent=2))
    return {**_public(stored), "delete_token": token}


def get_job(store_dir: str | Path, job_id: str) -> dict | None:
    job = _read_raw(store_dir, job_id)
    return _public(job) if job is not None else None


def update_job(store_dir: str | Path, job_id: str, **fields) -> dict | None:
    """Merge fields into a job's report and return the public view."""
    job = _read_raw(store_dir, job_id)
    if job is None:
        return None
    job.update(fields)
    (Path(store_dir) / job_id / "report.json").write_text(json.dumps(job, indent=2))
    return _public(job)


def delete_job(store_dir: str | Path, job_id: str, token: str | None) -> bool:
    """Delete a job with its submitter token. True if deleted, False
    if there is no such job. Raises PermissionError on a bad token."""
    job = _read_raw(store_dir, job_id)
    if job is None:
        return False
    if token is None:
        raise PermissionError("a delete token is required")
    given = hashlib.sha256(token.encode()).hexdigest()
    if not hmac.compare_digest(given, job.get("delete_token_hash", "")):
        raise PermissionError("delete token does not match")
    shutil.rmtree(Path(store_dir) / job_id)
    return True


def record_takedown_request(
    store_dir: str | Path, job_id: str, contact: str, reason: str
) -> dict:
    record = {
        "job_id": job_id,
        "contact": contact,
        "reason": reason,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    path = Path(store_dir) / ".takedown-requests.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    return record
