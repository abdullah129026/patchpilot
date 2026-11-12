"""Daily submission ceilings (Phase 2, decision D2).

One job at a time, a global daily ceiling tied to the Groq free-tier
token cap, and a per-address daily ceiling. Counts live in a single
counters file inside the job store, never in a job report, so the read
endpoint cannot leak them. Addresses are hashed before storage: the
counter needs to tell addresses apart, it does not need to keep them.

Phase 4 adds the kill switch: a `.paused` file in the job store
refuses new submissions and queued-job starts until it is removed.
There is no API to pause: v1 has no accounts, so a public pause
switch would be an abuse vector of its own.
"""

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app import config

_LOCK = threading.RLock()


class LimitExceeded(Exception):
    def __init__(self, kind: str, message: str, status_code: int = 429):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code


def is_paused(store_dir: str | Path) -> bool:
    """True while the founder's `.paused` file sits in the job store."""
    return (Path(store_dir) / ".paused").exists()


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # The reverse proxy (Caddy) appends the address it actually
        # saw, so the last entry is the real client; earlier entries
        # are client-supplied and can be spoofed to rotate the
        # per-IP ceiling. Single-proxy setup: the service binds
        # localhost and only Caddy reaches it.
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    if request.client is not None:
        return request.client.host
    return "unknown"


def _counters_path(store_dir: str | Path) -> Path:
    return Path(store_dir) / ".counters.json"


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load(store_dir: str | Path) -> dict:
    try:
        return json.loads(_counters_path(store_dir).read_text())
    except (OSError, ValueError):
        return {}


def _save(store_dir: str | Path, counters: dict) -> None:
    path = _counters_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counters, indent=2))


def _day(counters: dict, day: str) -> dict:
    return counters.setdefault("days", {}).setdefault(day, {"global": 0, "ips": {}})


def global_today(store_dir: str | Path) -> int:
    """Jobs submitted today, for the stats endpoint (Phase 4)."""
    counters = _load(store_dir)
    day = counters.get("days", {}).get(_today(), {"global": 0})
    return day["global"]


def usage(store_dir: str | Path, ip: str) -> dict:
    counters = _load(store_dir)
    day = counters.get("days", {}).get(_today(), {"global": 0, "ips": {}})
    per_ip = day["ips"].get(hashlib.sha256(ip.encode()).hexdigest(), 0)
    return {
        "daily_used": day["global"],
        "daily_ceiling": config.DAILY_JOB_CEILING,
        "per_ip_used": per_ip,
        "per_ip_ceiling": config.PER_IP_DAILY_CEILING,
    }


def check_limits(store_dir: str | Path, ip: str) -> None:
    if is_paused(store_dir):
        raise LimitExceeded(
            "paused",
            "PatchPilot is paused right now. No new jobs are accepted "
            "until the founder resumes the demo.",
            status_code=503,
        )
    used = usage(store_dir, ip)
    if used["daily_used"] >= config.DAILY_JOB_CEILING:
        raise LimitExceeded(
            "global",
            "Daily job limit reached (3 jobs per day while the demo runs "
            "on the free LLM tier). Try again tomorrow.",
        )
    if used["per_ip_used"] >= config.PER_IP_DAILY_CEILING:
        raise LimitExceeded(
            "per_ip",
            "You have reached the per-address daily limit (2 jobs per day). "
            "Try again tomorrow.",
        )


def check_and_record(store_dir: str | Path, ip: str) -> dict:
    """Check the ceilings and record the submission atomically.

    Check-then-record in two steps lets a burst of parallel
    submissions all pass the check before any of them records, and
    the global ceiling overshoots. One lock across both keeps the
    count honest.
    """
    with _LOCK:
        check_limits(store_dir, ip)
        return record_submission(store_dir, ip)


def record_submission(store_dir: str | Path, ip: str) -> dict:
    with _LOCK:
        counters = _load(store_dir)
        day = _day(counters, _today())
        day["global"] += 1
        key = hashlib.sha256(ip.encode()).hexdigest()
        day["ips"][key] = day["ips"].get(key, 0) + 1
        _save(store_dir, counters)
    return usage(store_dir, ip)


def record_rejection(store_dir: str | Path, kind: str) -> None:
    """Count a refused submission by kind, for the stats endpoint."""
    with _LOCK:
        counters = _load(store_dir)
        day = _day(counters, _today())
        rejected = day.setdefault("rejected", {})
        rejected[kind] = rejected.get(kind, 0) + 1
        _save(store_dir, counters)


def rejections_today(store_dir: str | Path) -> dict:
    counters = _load(store_dir)
    day = counters.get("days", {}).get(_today(), {})
    return dict(day.get("rejected", {}))
