"""First-party analytics events (Phase 4, Phase 0 section 0.5).

No cookies, no third party, no PII: an event is a name from the
allowlist plus an optional verdict. Nothing about the visitor is
recorded, no IP, no user agent, no issue URL. One JSON line per event
in the job store directory, so the stats endpoint can count them.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.verdicts import Verdict

EVENTS = frozenset(
    {
        "landing_view",
        "job_submitted",
        "job_started",
        "verdict_shown",
        "report_copied_script",
        "report_copied_test",
        "diff_expanded",
        "sample_report_opened",
    }
)

_EVENTS_FILE = "events.jsonl"


def record_event(store_dir: str | Path, name: str, verdict: str | None = None) -> dict:
    if name not in EVENTS:
        raise ValueError(f"unknown event: {name!r}")
    if verdict is not None and verdict not in {v.value for v in Verdict}:
        raise ValueError(f"unknown verdict: {verdict!r}")
    record = {
        "event": name,
        "verdict": verdict,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    path = Path(store_dir) / _EVENTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def event_counts(store_dir: str | Path) -> dict:
    path = Path(store_dir) / _EVENTS_FILE
    counts: dict[str, int] = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return counts
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        name = record.get("event")
        if name in EVENTS:
            counts[name] = counts.get(name, 0) + 1
    return counts


def verdict_distribution(store_dir: str | Path) -> dict:
    root = Path(store_dir)
    distribution: dict[str, int] = {}
    if not root.is_dir():
        return distribution
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            job = json.loads((child / "report.json").read_text())
        except (OSError, ValueError):
            continue
        verdict = job.get("verdict")
        if verdict in {v.value for v in Verdict}:
            distribution[verdict] = distribution.get(verdict, 0) + 1
    return distribution
