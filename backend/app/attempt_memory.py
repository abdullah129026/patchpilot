"""Cross-job attempt memory (improvement track, roadmap item 1a).

Today every attempt lives only inside its own job's report, so a job
that repeats a failed approach from last week has no way to know.
This module appends one JSONL line per attempt to
``<store_dir>/.attempt-memory.jsonl`` when a job finishes: repo,
language, error signature, attempt number, failure type, exit code,
and the script and log tail capped so one pathological run cannot
bloat the file. Retrieval (1b) and near-duplicate rejection (1c)
read this file; this slice only stores.

Failure types: syntax_error (no container run was spent), timeout,
wrong_error_signature (non-zero exit but the issue's error never
appeared), exit_zero_no_repro (the script ran clean, the bug never
fired), setup_failure (clone, checkout, install, or unsupported
stack, recorded with no script), reproduced, and other_nonzero as
the fallback for a non-zero exit whose signature did match without
reproducing (unreachable through the pipeline, kept so the
classifier is total).

Recording is idempotent per (job_id, attempt n) and best-effort: a
store failure never fails the job, so the pipeline calls it from a
try/except. The file sits next to the job directories, the same
pattern as the takedown-requests JSONL in the job store.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.job_store import get_job
from app.verdicts import signature_in_log

MEMORY_FILE = ".attempt-memory.jsonl"
# The store keeps a script and a log tail, not whole artifacts: the
# job report already holds the full text, memory only needs enough
# to recognize the approach again.
MAX_MEMORY_SCRIPT_CHARS = 4000
MAX_MEMORY_LOG_TAIL_CHARS = 2000
# v1 has one strategy: each attempt is the previous attempt's
# feedback applied to the same prompt. Varied strategies are
# roadmap item 3; the field exists now so later runs can compare.
STRATEGY = "feedback_loop"

# Details the pipeline finishes with when no attempt ever ran.
# Anything else with zero attempts records nothing: an
# underspecified issue or a missing LLM is not a failed approach.
_SETUP_DETAILS = {
    "repo clone failed",
    "repo checkout failed",
    "dependency install failed",
    "stack not supported for reproduction in v1",
}


def classify_failure(attempt: dict, signature: str | None, reproduced: bool) -> str:
    """Failure type for one attempt, from its own evidence only."""
    if reproduced:
        return "reproduced"
    # Timeout first: a timed-out run has no exit code either, and a
    # syntax failure never reaches the container, so timed_out can
    # only mean the run itself was cut off.
    if attempt.get("timed_out"):
        return "timeout"
    if attempt.get("exit_code") is None:
        return "syntax_error"
    if attempt.get("exit_code") == 0:
        return "exit_zero_no_repro"
    log = attempt.get("log") or ""
    if signature and not signature_in_log(signature, log):
        return "wrong_error_signature"
    return "other_nonzero"


def _record(job, attempt, n, failure_type) -> dict:
    issue = job.get("issue") or {}
    script = attempt.get("script") or ""
    log = attempt.get("log") or ""
    return {
        "job_id": job["id"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "repo": f"{issue.get('owner')}/{issue.get('repo')}",
        "issue": issue.get("number"),
        "language": job.get("stack"),
        "signature": job.get("signature"),
        "n": n,
        "strategy": STRATEGY,
        "failure_type": failure_type,
        "exit_code": attempt.get("exit_code"),
        "script": script[:MAX_MEMORY_SCRIPT_CHARS],
        "log_tail": log[-MAX_MEMORY_LOG_TAIL_CHARS:],
    }


def _already_recorded(path: Path, job_id: str) -> set:
    """Attempt numbers already stored for this job, so a second
    recording pass (a retry, a re-read) never duplicates a line."""
    recorded = set()
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return recorded
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("job_id") == job_id and isinstance(record.get("n"), int):
            recorded.add(record["n"])
    return recorded


def record_attempts(store_dir, job_id: str) -> int:
    """Append this job's attempts to the memory file. Returns how
    many lines were written. A job with no attempts and no setup
    failure writes nothing."""
    job = get_job(store_dir, job_id)
    if job is None:
        return 0
    path = Path(store_dir) / MEMORY_FILE
    recorded = _already_recorded(path, job_id)
    attempts = job.get("attempts") or []
    lines = []
    if attempts:
        reproduced = bool(job.get("repro_script"))
        for index, attempt in enumerate(attempts):
            n = attempt.get("n", index + 1)
            if n in recorded:
                continue
            # The loop stops on a reproduction, so the reproducing
            # attempt is the last one when a repro script exists.
            is_repro = reproduced and index == len(attempts) - 1
            lines.append(
                _record(
                    job,
                    attempt,
                    n,
                    classify_failure(attempt, job.get("signature"), is_repro),
                )
            )
    elif job.get("detail") in _SETUP_DETAILS and 0 not in recorded:
        lines.append(
            _record(
                job,
                {"exit_code": None, "script": "", "log": job.get("detail")},
                0,
                "setup_failure",
            )
        )
    if not lines:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        for record in lines:
            handle.write(json.dumps(record) + "\n")
    return len(lines)


def read_attempts(store_dir) -> list:
    """All stored attempts, oldest first. Malformed lines are
    skipped, never fatal: the file is append-only and hand-editable."""
    path = Path(store_dir) / MEMORY_FILE
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records
