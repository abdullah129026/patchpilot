import json

from app import attempt_memory, pipeline
from app.attempt_memory import classify_failure, read_attempts, record_attempts
from app.job_store import create_job
from app.runner import RunResult

ISSUE = {"title": "Crash on empty config", "body": "Traceback:\nValueError: bad key\n"}


class ReproExecutor:
    """The script exits 1 with the issue's error in the log."""

    def install(self, workspace, stack):
        return RunResult(exit_code=0, log="installed\n")

    def run(self, workspace, stack, command):
        if command == ["python", "repro.py"]:
            return RunResult(exit_code=1, log="Traceback:\nValueError: bad key\n")
        if command[0:3] == ["python", "-m", "pytest"]:
            app = workspace / "app.py"
            if app.exists() and "data.get(key)" in app.read_text():
                return RunResult(exit_code=0, log="1 passed\n")
            return RunResult(exit_code=1, log="FAILED test\n")
        return RunResult(exit_code=0, log="ok\n")


class ReproLLM:
    def complete(self, prompt):
        if "failing test" in prompt:
            return "def test_empty_config():\n    assert load({}) is not None\n"
        if "fix diff" in prompt:
            return (
                "--- a/app.py\n+++ b/app.py\n"
                "@@ -1,1 +1,1 @@\n"
                "-return data[key]  # buggy\n"
                "+return data.get(key)\n"
            )
        return 'config = {}\nprint(config["missing"])\n'


class WrongSignatureExecutor(ReproExecutor):
    """Non-zero exit, but the issue's error never appears."""

    def run(self, workspace, stack, command):
        if command == ["python", "repro.py"]:
            return RunResult(exit_code=1, log="Traceback:\nKeyError: other\n")
        return RunResult(exit_code=0, log="ok\n")


class TimeoutExecutor(ReproExecutor):
    def run(self, workspace, stack, command):
        return RunResult(exit_code=None, log="still running\n", timed_out=True)


class FailingInstallExecutor(ReproExecutor):
    def install(self, workspace, stack):
        return RunResult(exit_code=1, log="pip failed\n")


class SyntaxErrorLLM:
    def complete(self, prompt):
        return "def broken(:\n"


def _clone_with_buggy_app(owner, repo, dest):
    dest.mkdir(parents=True)
    (dest / "app.py").write_text("return data[key]  # buggy\n")


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "MAX_ATTEMPTS", 2)
    job = create_job(tmp_path, "acme", "demo", 7)
    return job["id"]


def _run(tmp_path, monkeypatch, executor, llm):
    job_id = _setup(tmp_path, monkeypatch)
    job = pipeline.run_job(
        tmp_path,
        job_id,
        issue=ISSUE,
        clone_fn=_clone_with_buggy_app,
        executor=executor,
        llm=llm,
    )
    return job_id, job


def _memory_lines(tmp_path):
    path = tmp_path / ".attempt-memory.jsonl"
    assert path.exists()
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_reproduced_job_records_one_reproduced_line(tmp_path, monkeypatch):
    job_id, job = _run(tmp_path, monkeypatch, ReproExecutor(), ReproLLM())
    assert job["verdict"] == "REPRODUCED"
    lines = _memory_lines(tmp_path)
    assert len(lines) == 1
    record = lines[0]
    assert record["job_id"] == job_id
    assert record["repo"] == "acme/demo"
    assert record["issue"] == 7
    assert record["language"] == "python"
    assert record["signature"] == "ValueError: bad key"
    assert record["n"] == 1
    assert record["strategy"] == "feedback_loop"
    assert record["failure_type"] == "reproduced"
    assert record["exit_code"] == 1
    assert "config[" in record["script"]


def test_wrong_signature_records_each_attempt(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, WrongSignatureExecutor(), ReproLLM())
    lines = _memory_lines(tmp_path)
    assert len(lines) == 2
    assert [line["failure_type"] for line in lines] == [
        "wrong_error_signature",
        "wrong_error_signature",
    ]
    assert [line["n"] for line in lines] == [1, 2]


def test_syntax_error_records_no_container_run(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, ReproExecutor(), SyntaxErrorLLM())
    lines = _memory_lines(tmp_path)
    assert len(lines) == 2
    assert lines[0]["failure_type"] == "syntax_error"
    assert lines[0]["exit_code"] is None


def test_timeout_records_timeout_type(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, TimeoutExecutor(), ReproLLM())
    lines = _memory_lines(tmp_path)
    assert len(lines) == 1
    assert lines[0]["failure_type"] == "timeout"


def test_setup_failure_records_one_line_with_no_script(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, FailingInstallExecutor(), ReproLLM())
    lines = _memory_lines(tmp_path)
    assert len(lines) == 1
    assert lines[0]["failure_type"] == "setup_failure"
    assert lines[0]["n"] == 0
    assert lines[0]["script"] == ""


def test_recording_is_idempotent(tmp_path, monkeypatch):
    job_id, _job = _run(tmp_path, monkeypatch, ReproExecutor(), ReproLLM())
    assert record_attempts(tmp_path, job_id) == 0
    assert len(_memory_lines(tmp_path)) == 1


def test_script_and_log_are_capped(tmp_path, monkeypatch):
    class LongLLM(ReproLLM):
        def complete(self, prompt):
            if "failing test" in prompt or "fix diff" in prompt:
                return super().complete(prompt)
            return "x = '" + "a" * 6000 + "'\nprint(x[0])\n"

    _run(tmp_path, monkeypatch, ReproExecutor(), LongLLM())
    lines = _memory_lines(tmp_path)
    assert len(lines[0]["script"]) <= attempt_memory.MAX_MEMORY_SCRIPT_CHARS
    assert len(lines[0]["log_tail"]) <= attempt_memory.MAX_MEMORY_LOG_TAIL_CHARS


def test_classify_failure_covers_each_type():
    assert classify_failure({"exit_code": None}, "ValueError", False) == "syntax_error"
    assert (
        classify_failure({"exit_code": None, "timed_out": True}, "ValueError", False)
        == "timeout"
    )
    assert (
        classify_failure({"exit_code": 1, "timed_out": True}, "ValueError", False)
        == "timeout"
    )
    assert (
        classify_failure({"exit_code": 0, "log": "ok"}, "ValueError", False)
        == "exit_zero_no_repro"
    )
    assert (
        classify_failure(
            {"exit_code": 1, "log": "KeyError: other"}, "ValueError", False
        )
        == "wrong_error_signature"
    )
    assert (
        classify_failure(
            {"exit_code": 1, "log": "ValueError: bad key"}, "ValueError", True
        )
        == "reproduced"
    )
    assert (
        classify_failure({"exit_code": 1, "log": "ValueError: bad key"}, None, False)
        == "other_nonzero"
    )


def test_read_attempts_empty_and_malformed(tmp_path):
    assert read_attempts(tmp_path) == []
    path = tmp_path / ".attempt-memory.jsonl"
    path.write_text('{"job_id": "abc", "n": 1}\nnot json\n')
    assert read_attempts(tmp_path) == [{"job_id": "abc", "n": 1}]


def test_record_attempts_unknown_job_writes_nothing(tmp_path):
    assert record_attempts(tmp_path, "0123456789ab") == 0
    assert not (tmp_path / ".attempt-memory.jsonl").exists()
