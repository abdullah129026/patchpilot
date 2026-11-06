"""Docker runner (Phase 3, ADR-006): untrusted code runs only here.

Two phases, enforced by the command line, not by prompts: install
runs with the default network so dependencies can be fetched, and
every script run uses --network none. Job containers get no socket
mount, no privileged flag, dropped capabilities, and CPU/memory caps;
the only host path they see is their own workspace. The command is
always a list, never a shell string, and the workspace is the caller's
to delete afterwards. docker-py is deliberately not used: its
containers.run raises on the non-zero exits a correct reproduction
produces, and hides stderr by default.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app import config

_IMAGES = {
    "python": config.PYTHON_IMAGE,
    "javascript": config.NODE_IMAGE,
    "cpp": config.CPP_IMAGE,
}

# Installs land in the workspace, not the install container's own
# site-packages: install and run are separate `docker run --rm`
# containers, so only the mounted workspace survives between them.
DEPS_DIR = "/work/.patchpilot_deps"


@dataclass
class RunResult:
    exit_code: int | None
    log: str
    timed_out: bool = False


def _truncate(log: str) -> str:
    if len(log) <= config.MAX_LOG_CHARS:
        return log
    head = config.MAX_LOG_CHARS // 5
    return log[:head] + "\n[log truncated]\n" + log[-(config.MAX_LOG_CHARS - head) :]


class DockerRunner:
    def __init__(
        self,
        docker: str = "docker",
        timeout: int | None = None,
        env: dict | None = None,
    ):
        self.docker = docker
        self.timeout = timeout or config.RUN_TIMEOUT_SECONDS
        self.env = env

    def image_for(self, stack: str) -> str:
        return _IMAGES[stack]

    def _run_container(
        self, workspace: Path, stack: str, command: list[str], network_off: bool
    ) -> RunResult:
        # Docker treats a non-absolute -v source as a named volume, and
        # slashes are not valid volume-name characters, so a relative
        # workspace must be resolved before it goes into the mount.
        workspace = Path(workspace).resolve()
        cmd = [
            self.docker,
            "run",
            "--rm",
            "--cpus",
            config.RUN_CPUS,
            "--memory",
            config.RUN_MEMORY,
            "--cap-drop",
            "ALL",
            # With capabilities dropped, container root loses
            # CAP_DAC_OVERRIDE and cannot write into a workspace owned
            # by the host user; run as the workspace owner instead.
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--pids-limit",
            "64",
            "-v",
            f"{workspace}:/work:rw",
            "-w",
            "/work",
        ]
        if stack == "python":
            cmd += ["-e", f"PYTHONPATH={DEPS_DIR}"]
        if network_off:
            cmd += ["--network", "none"]
        cmd += [self.image_for(stack), *command]
        run_env = {**os.environ, **(self.env or {})}
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=run_env,
            )
            return RunResult(
                exit_code=proc.returncode,
                log=_truncate(proc.stdout + proc.stderr),
            )
        except subprocess.TimeoutExpired as exc:
            out = (
                (exc.stdout or b"")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            err = (
                (exc.stderr or b"")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            )
            return RunResult(
                exit_code=None, log=_truncate(str(out) + str(err)), timed_out=True
            )

    def install(self, workspace: str | Path, stack: str) -> RunResult:
        workspace = Path(workspace)
        if stack == "python":
            if (workspace / "pyproject.toml").exists() or (
                workspace / "setup.py"
            ).exists():
                # Installing the project itself also pulls its deps.
                return self._run_container(
                    workspace,
                    stack,
                    ["pip", "install", "--target", DEPS_DIR, "."],
                    network_off=False,
                )
            if (workspace / "requirements.txt").exists():
                return self._run_container(
                    workspace,
                    stack,
                    [
                        "pip",
                        "install",
                        "-r",
                        "requirements.txt",
                        "--target",
                        DEPS_DIR,
                    ],
                    network_off=False,
                )
        if stack == "javascript" and (workspace / "package-lock.json").exists():
            return self._run_container(
                workspace,
                stack,
                ["npm", "ci", "--no-audit", "--no-fund"],
                network_off=False,
            )
        return RunResult(exit_code=0, log="no install step for this repo\n")

    def run(self, workspace: str | Path, stack: str, command: list[str]) -> RunResult:
        return self._run_container(Path(workspace), stack, command, network_off=True)

    @staticmethod
    def cleanup(workspace: str | Path) -> None:
        shutil.rmtree(workspace, ignore_errors=True)
