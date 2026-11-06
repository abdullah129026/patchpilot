import os
import stat
from pathlib import Path

from app.runner import DockerRunner


def _fake_docker(tmp_path, body):
    script = tmp_path / "docker"
    script.write_text("#!/bin/sh\n" 'echo "$@" >> "$FAKE_DOCKER_ARGS"\n' + body)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def test_run_is_network_off_capped_and_unprivileged(tmp_path):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(
        tmp_path,
        "echo 'ValueError: bad key' >&2\n" "exit 1\n",
    )
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    result = runner.run(tmp_path / "ws", "python", ["python", "repro.py"])
    assert result.exit_code == 1
    assert "ValueError: bad key" in result.log
    args = args_file.read_text()
    assert "--network none" in args
    assert "--cap-drop ALL" in args
    assert "--memory" in args and "--cpus" in args
    assert "--privileged" not in args
    assert "docker.sock" not in args
    assert "/var/run" not in args


def test_run_resolves_relative_workspace_for_volume_mount(tmp_path, monkeypatch):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(tmp_path, "exit 0\n")
    monkeypatch.chdir(tmp_path)
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    relative_ws = Path("data/fixture-runs/job1/workspace")
    result = runner.run(relative_ws, "python", ["python", "repro.py"])
    assert result.exit_code == 0
    expected = str((tmp_path / relative_ws).resolve())
    assert f"-v {expected}:/work:rw" in args_file.read_text()


def test_install_runs_with_network_on(tmp_path):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(tmp_path, "exit 0\n")
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    (tmp_path / "ws").mkdir()
    (tmp_path / "ws" / "requirements.txt").write_text("requests\n")
    result = runner.install(tmp_path / "ws", "python")
    assert result.exit_code == 0
    assert "--network none" not in args_file.read_text()


def test_install_pyproject_installs_project_into_workspace_deps(tmp_path):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(tmp_path, "exit 0\n")
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    # Project files win even when a requirements.txt is also present.
    (ws / "requirements.txt").write_text("requests\n")
    result = runner.install(ws, "python")
    assert result.exit_code == 0
    args = args_file.read_text()
    assert "pip install --target /work/.patchpilot_deps ." in args
    assert "--network none" not in args


def test_install_requirements_only_uses_workspace_deps_target(tmp_path):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(tmp_path, "exit 0\n")
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "requirements.txt").write_text("requests\n")
    result = runner.install(ws, "python")
    assert result.exit_code == 0
    assert (
        "pip install -r requirements.txt --target /work/.patchpilot_deps"
        in args_file.read_text()
    )


def test_python_run_gets_deps_dir_on_pythonpath(tmp_path):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(tmp_path, "exit 0\n")
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    result = runner.run(tmp_path / "ws", "python", ["python", "repro.py"])
    assert result.exit_code == 0
    assert "-e PYTHONPATH=/work/.patchpilot_deps" in args_file.read_text()


def test_run_container_runs_as_workspace_owner(tmp_path):
    args_file = tmp_path / "args.txt"
    args_file.write_text("")
    docker = _fake_docker(tmp_path, "exit 0\n")
    runner = DockerRunner(docker=docker, env={"FAKE_DOCKER_ARGS": str(args_file)})
    result = runner.run(tmp_path / "ws", "python", ["python", "repro.py"])
    assert result.exit_code == 0
    assert f"--user {os.getuid()}:{os.getgid()}" in args_file.read_text()


def test_run_timeout_is_reported_not_raised(tmp_path):
    docker = _fake_docker(tmp_path, "sleep 5\n")
    runner = DockerRunner(docker=docker, timeout=1)
    result = runner.run(tmp_path / "ws", "python", ["python", "repro.py"])
    assert result.timed_out is True
    assert result.exit_code is None


def test_log_is_capped(tmp_path):
    docker = _fake_docker(tmp_path, "head -c 40000 /dev/zero | tr '\\0' 'x'\n")
    runner = DockerRunner(docker=docker)
    result = runner.run(tmp_path / "ws", "python", ["python", "repro.py"])
    assert len(result.log) <= 21000
