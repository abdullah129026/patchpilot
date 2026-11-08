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
import subprocess
import time
from pathlib import Path

from app import config, stack as stack_mod
from app.analyzer import analyze_issue
from app.github_client import checkout_ref, clone_repo, fetch_issue_cached
from app.job_store import get_job, update_job
from app.llm import ProviderUnavailable, build_llm_client
from app.runner import DockerRunner
from app.verdicts import compute_verdict, signature_in_log

MAX_ATTEMPTS = config.MAX_ATTEMPTS

# ponytail: single-file diffs only in v1. Multi-file fixes are a real
# need, but parsing them correctly is its own project; a diff touching
# more than one file is recorded as unverified rather than half-applied.
_REPRO_FILE = {
    "python": "repro.py",
    "javascript": "repro.js",
    "cpp": "repro.cpp",
}
# C++ needs a compile step before the run; the steps run in order and
# the first non-zero result stops the sequence, so a compile failure
# is the attempt's result, not a spent reproduction run.
_REPRO_COMMANDS = {
    "python": [["python", "repro.py"]],
    "javascript": [["node", "repro.js"]],
    "cpp": [
        ["g++", "-std=c++17", "-O0", "-o", "repro", "repro.cpp"],
        ["./repro"],
    ],
}
_TEST_FILE = {
    "python": "test_patchpilot_generated.py",
    "javascript": "test_patchpilot_generated.test.js",
    "cpp": "test_patchpilot_generated.cpp",
}
# Generated tests are standalone in v1 (D4 for C++): no framework
# detection, just an exit code. The same shape works for JS, where
# node runs the file directly instead of through a test runner.
_TEST_COMMANDS = {
    "python": [["python", "-m", "pytest", "test_patchpilot_generated.py", "-q"]],
    "javascript": [["node", "test_patchpilot_generated.test.js"]],
    "cpp": [
        [
            "g++",
            "-std=c++17",
            "-O0",
            "-o",
            "test_patchpilot_generated",
            "test_patchpilot_generated.cpp",
        ],
        ["./test_patchpilot_generated"],
    ],
}
_SCRIPT_HINT = {
    "python": "a Python script",
    "javascript": "a JavaScript script",
    "cpp": "a complete standalone C++ program with main()",
}
_TEST_HINT = {
    "python": "a pytest test",
    "javascript": "a standalone script that exits non-zero when the bug is present, "
    "no test framework",
    "cpp": "a standalone program with main() that exits non-zero when the "
    "bug is present, no test framework",
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


def _strip_code_fence(text: str) -> str:
    """Return the first fenced code block in an LLM reply, else the reply.

    Real models fence generated code despite being told to reply with
    code only, and a fence line makes the written file unparseable
    (Qwen fenced all 60 scripts in the first live fixture run, so zero
    container runs were spent). Only the first block is taken: the
    artifact the prompt asked for, prose around it is chat.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            body = []
            for rest in lines[i + 1 :]:
                if rest.lstrip().startswith("```"):
                    break
                body.append(rest)
            return "\n".join(body) + "\n" if body else ""
    return text


def _script_is_valid(stack: str, path: Path) -> bool:
    """Syntax-check a generated script before a container run is spent.

    # ponytail: the check runs on the workspace file (not a temp copy)
    so C++ includes resolve against the repo, and when the local
    toolchain is missing the check is skipped rather than faked: the
    container run then surfaces the error, and the attempt still counts.
    """
    if stack == "python":
        try:
            ast.parse(path.read_text())
        except (SyntaxError, OSError):
            return False
        return True
    tool, command = {
        "javascript": ("node", ["node", "--check", str(path)]),
        "cpp": ("g++", ["g++", "-fsyntax-only", str(path)]),
    }.get(stack, (None, None))
    if tool is None or shutil.which(tool) is None:
        return True
    try:
        proc = subprocess.run(command, cwd=path.parent, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return True
    return proc.returncode == 0


def _run_steps(executor, workspace, stack, commands):
    """Run a command sequence; the first failure stops it."""
    result = None
    for command in commands:
        result = executor.run(workspace, stack, command)
        if result.timed_out or result.exit_code not in (None, 0):
            break
    return result


def _finish(store_dir, job_id, **fields):
    return update_job(store_dir, job_id, **fields)


def _charge(llm, total: int) -> int:
    """Add the last LLM call's reported usage to the running total.
    A client that reports nothing (fake in tests, a provider that
    omits usage) adds zero rather than breaking the job."""
    usage = getattr(llm, "last_usage", None) or {}
    return total + usage.get("input", 0) + usage.get("output", 0)


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
    update_job(store_dir, job_id, status="running", tokens_used=0)
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
    # Fixture jobs run the repo at the recorded pre-fix commit, so the
    # bug is actually present. Public jobs have no ref and run HEAD.
    if meta.get("ref"):
        try:
            checkout_ref(workspace, meta["ref"])
        except Exception:
            return _finish(
                store_dir,
                job_id,
                status="done",
                verdict=compute_verdict(None, False, setup_failed=True).value,
                signature=signature,
                detail="repo checkout failed",
            )
    detected = stack_mod.detect(stack_mod.list_files(workspace))
    if detected is None or detected not in _REPRO_FILE:
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
    tokens_used = 0
    for n in range(1, MAX_ATTEMPTS + 1):
        if time.monotonic() - started > config.MAX_JOB_SECONDS:
            limit_reached = True
            break
        script = _strip_code_fence(
            llm.complete(
                f"Write {_SCRIPT_HINT[detected]} that reproduces this issue. "
                "Reply with only the script code. The script must exit "
                "non-zero and leave the error in its output when the bug "
                "is present; do not catch or swallow the error.\n"
                f"Issue: {issue['title']}\n{issue['body'] or ''}"
            )
        )
        tokens_used = _charge(llm, tokens_used)
        update_job(store_dir, job_id, tokens_used=tokens_used)
        script_path = workspace / _REPRO_FILE[detected]
        script_path.write_text(script)
        if not _script_is_valid(detected, script_path):
            attempts.append(
                {
                    "n": n,
                    "exit_code": None,
                    "log": "script failed syntax check, no container run spent",
                    "script": script,
                }
            )
            update_job(store_dir, job_id, attempts=attempts)
            continue
        result = _run_steps(executor, workspace, detected, _REPRO_COMMANDS[detected])
        attempts.append(
            {"n": n, "exit_code": result.exit_code, "log": result.log, "script": script}
        )
        # Attempts are written as they land, so the live job view
        # shows progress instead of waiting for the final verdict.
        update_job(store_dir, job_id, attempts=attempts)
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
    test = _strip_code_fence(
        llm.complete(
            f"Write {_TEST_HINT[detected]} as a failing test that captures "
            f"this bug. Reply with only the test code.\nIssue: {issue['title']}\n"
            f"Reproduction script:\n{reproduced}"
        )
    )
    tokens_used = _charge(llm, tokens_used)
    update_job(store_dir, job_id, tokens_used=tokens_used)
    test_name = _TEST_FILE[detected]
    (workspace / test_name).write_text(test)
    fields["failing_test"] = test
    fields["fix_verified"] = False
    before = _run_steps(executor, workspace, detected, _TEST_COMMANDS[detected])
    if before.exit_code in (None, 0):
        # A test that already passes is not a failing test; no fix
        # is proposed off it, and no verified label is claimed.
        fields["detail"] = "generated test passed before any fix; no fix proposed"
        return _finish(store_dir, job_id, **fields)
    diff = llm.complete(
        "Write a fix diff for this bug. Reply with only the unified "
        f"diff.\nIssue: {issue['title']}\nFailing test:\n{test}"
    )
    tokens_used = _charge(llm, tokens_used)
    update_job(store_dir, job_id, tokens_used=tokens_used)
    fields["fix_diff"] = diff
    try:
        apply_diff(workspace, diff)
    except ValueError:
        fields["detail"] = "fix diff could not be applied cleanly; not verified"
        return _finish(store_dir, job_id, **fields)
    after = _run_steps(executor, workspace, detected, _TEST_COMMANDS[detected])
    fields["fix_verified"] = after.exit_code == 0
    return _finish(store_dir, job_id, **fields)
