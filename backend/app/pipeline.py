"""The reproduction loop (Phase 3, ADR-002 fixed pipeline).

Stages, in order: fetch the issue, extract its error signature and
run the quality check, clone, detect the stack, install, then the
attempt loop with deterministic matching. A REPRODUCED job goes on to
a generated failing test and a fix diff whose VERIFIED label comes
only from the test failing before the fix and passing after.

Nothing the issue says is ever executed: the executor only ever runs
the generated script file, and the generated test, inside a network-off
container. The LLM proposes; this module disposes. Token and time
ceilings stop the loop with LIMIT REACHED rather than a verdict the
job never earned. Workspaces are deleted at job end in all paths;
the report keeps the capped logs.
"""

import ast
import shutil
import time
from pathlib import Path

from app import config, stack as stack_mod
from app.analyzer import analyze_issue
from app.github_client import clone_repo, fetch_issue_cached
from app.job_store import get_job, update_job
from app.llm import ProviderUnavailable, build_llm_client
from app.runner import DockerRunner
from app.verdicts import compute_verdict, signature_in_log

MAX_ATTEMPTS = config.MAX_ATTEMPTS

# ponytail: single-file diffs only in v1. Multi-file fixes are a real
# need, but parsing them correctly is its own project; a diff touching
# more than one file is recorded as unverified rather than half-applied.
_TEST_FILE = {"python": "test_patchpilot_generated.py"}
_REPRO_COMMAND = {"python": ["python", "repro.py"]}
_TEST_COMMAND = {
    "python": ["python", "-m", "pytest", "test_patchpilot_generated.py", "-q"],
}


def apply_diff(workspace: str | Path, diff: str) -> None:
    """Apply a single-file unified diff to a workspace file.

    Raises ValueError on escaping paths, new-file diffs, or hunks
    whose removed lines do not match the file on disk.
    """
    workspace = Path(workspace)
    sections = []
    current = None
    for line in diff.splitlines():
        if line.startswith("--- "):
            current = {"old": line[4:].strip(), "new": None, "hunks": []}
            sections.append(current)
        elif line.startswith("+++ ") and current is not None:
            current["new"] = line[4:].strip()
        elif current is not None and not line.startswith("@@"):
            if line.startswith((" ", "-", "+", "\\")) or line == "":
                current["hunks"].append(line)
    if len(sections) != 1:
        raise ValueError("only single-file diffs are supported in v1")
    section = sections[0]
    for path in (section["old"], section["new"]):
        if path is None or path.startswith("/") or ".." in Path(path).parts:
            raise ValueError(f"unsafe path in diff: {path!r}")
    target = section["new"]
    if target.startswith("b/"):
        target = target[2:]
    if section["old"] in ("/dev/null", "b/dev/null"):
        raise ValueError("new-file diffs are not applied in v1")
    file_path = workspace / target
    if not file_path.exists():
        raise ValueError(f"diff target does not exist in workspace: {target!r}")
    original = file_path.read_text().splitlines(keepends=True)
    out, idx = [], 0
    for line in section["hunks"]:
        if line.startswith("+"):
            out.append(line[1:] + "\n")
        elif line.startswith("-"):
            expected = line[1:]
            if idx >= len(original) or original[idx].rstrip("\n") != expected:
                raise ValueError("diff does not match the file on disk")
            idx += 1
        else:
            # Context line (or a blank line): copy the original through.
            if idx < len(original):
                out.append(original[idx])
                idx += 1
    out.extend(original[idx:])
    file_path.write_text("".join(out))


def _script_is_valid(stack: str, script: str) -> bool:
    if stack == "python":
        try:
            ast.parse(script)
        except SyntaxError:
            return False
    return True


def _finish(store_dir, job_id, **fields):
    return update_job(store_dir, job_id, **fields)


def run_job(store_dir, job_id, *, issue=None, clone_fn=None, executor=None, llm=None):
    """Run one job's pipeline to a verdict. Returns the public job."""
    job = get_job(store_dir, job_id)
    if job is None:
        return None
    clone_fn = clone_fn or clone_repo
    executor = executor or DockerRunner()
    if llm is None:
        try:
            llm = build_llm_client()
        except ProviderUnavailable:
            llm = None
    started = time.monotonic()
    workspace = Path(store_dir) / job_id / "workspace"
    update_job(store_dir, job_id, status="running")
    try:
        return _run(
            store_dir, job_id, job, workspace, issue, clone_fn, executor, llm, started
        )
    except Exception as exc:
        update_job(
            store_dir,
            job_id,
            status="failed",
            detail=f"pipeline failed: {type(exc).__name__}",
        )
        return get_job(store_dir, job_id)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _run(store_dir, job_id, job, workspace, issue, clone_fn, executor, llm, started):
    meta = job["issue"]
    if issue is None:
        try:
            issue = fetch_issue_cached(
                store_dir, job_id, meta["owner"], meta["repo"], meta["number"]
            )
        except Exception:
            return _finish(
                store_dir,
                job_id,
                status="done",
                verdict=compute_verdict(None, False, setup_failed=True).value,
                detail="issue fetch failed",
            )
    analysis = analyze_issue(issue)
    if analysis["underspecified"]:
        return _finish(
            store_dir,
            job_id,
            status="done",
            verdict=compute_verdict(None, False, underspecified=True).value,
            signature=None,
            detail="no error signature in the issue; nothing to match against",
        )
    signature = analysis["signature"]
    try:
        clone_fn(meta["owner"], meta["repo"], workspace)
    except Exception:
        return _finish(
            store_dir,
            job_id,
            status="done",
            verdict=compute_verdict(None, False, setup_failed=True).value,
            signature=signature,
            detail="repo clone failed",
        )
    detected = stack_mod.detect(stack_mod.list_files(workspace))
    if detected is None or detected not in _REPRO_COMMAND:
        return _finish(
            store_dir,
            job_id,
            status="done",
            verdict=compute_verdict(None, False, setup_failed=True).value,
            signature=signature,
            stack=detected,
            detail="stack not supported for reproduction in v1",
        )
    install = executor.install(workspace, detected)
    if install.exit_code != 0:
        return _finish(
            store_dir,
            job_id,
            status="done",
            verdict=compute_verdict(None, False, setup_failed=True).value,
            signature=signature,
            stack=detected,
            detail="dependency install failed",
        )
    if llm is None:
        return _finish(
            store_dir,
            job_id,
            status="failed",
            verdict=None,
            signature=signature,
            stack=detected,
            detail="LLM provider is not configured, so no "
            "reproduction script could be generated. No verdict "
            "is claimed for this job.",
        )
    attempts, limit_reached, reproduced = [], False, None
    for n in range(1, MAX_ATTEMPTS + 1):
        if time.monotonic() - started > config.MAX_JOB_SECONDS:
            limit_reached = True
            break
        script = llm.complete(
            "Write a reproduction script for this issue. Reply with only "
            f"the script code.\nIssue: {issue['title']}\n{issue['body'] or ''}"
        )
        if not _script_is_valid(detected, script):
            attempts.append(
                {
                    "n": n,
                    "exit_code": None,
                    "log": "script failed syntax check, no container run spent",
                    "script": script,
                }
            )
            continue
        (workspace / "repro.py").write_text(script)
        result = executor.run(workspace, detected, _REPRO_COMMAND[detected])
        attempts.append(
            {"n": n, "exit_code": result.exit_code, "log": result.log, "script": script}
        )
        if result.timed_out:
            limit_reached = True
            break
        if result.exit_code not in (None, 0) and signature_in_log(
            signature, result.log
        ):
            reproduced = script
            break
    verdict = compute_verdict(
        attempts[-1]["exit_code"] if attempts else None,
        bool(reproduced),
        limit_reached=limit_reached,
    )
    fields = {
        "status": "done",
        "verdict": verdict.value,
        "signature": signature,
        "stack": detected,
        "attempts": attempts,
        "fix_verified": False,
    }
    if not reproduced:
        return _finish(store_dir, job_id, **fields)
    fields["repro_script"] = reproduced
    test = llm.complete(
        "Write a failing test that captures this bug. Reply with only "
        f"the test code.\nIssue: {issue['title']}\nReproduction script:\n{reproduced}"
    )
    test_name = _TEST_FILE[detected]
    (workspace / test_name).write_text(test)
    fields["failing_test"] = test
    fields["fix_verified"] = False
    before = executor.run(workspace, detected, _TEST_COMMAND[detected])
    if before.exit_code in (None, 0):
        # A test that already passes is not a failing test; no fix
        # is proposed off it, and no verified label is claimed.
        fields["detail"] = "generated test passed before any fix; no fix proposed"
        return _finish(store_dir, job_id, **fields)
    diff = llm.complete(
        "Write a fix diff for this bug. Reply with only the unified "
        f"diff.\nIssue: {issue['title']}\nFailing test:\n{test}"
    )
    fields["fix_diff"] = diff
    try:
        apply_diff(workspace, diff)
    except ValueError:
        fields["detail"] = "fix diff could not be applied cleanly; not verified"
        return _finish(store_dir, job_id, **fields)
    after = executor.run(workspace, detected, _TEST_COMMAND[detected])
    fields["fix_verified"] = after.exit_code == 0
    return _finish(store_dir, job_id, **fields)
