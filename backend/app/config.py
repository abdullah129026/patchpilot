"""Ceilings and model config, from Phase 0 sections 0.2 and 0.3.

One place for every number that stops a job. Phase 2 wires the per-IP
and global daily ceilings into the submission path; the constants land
here in Phase 1 so nothing later invents its own limit.
"""

import os as _os

MAX_ATTEMPTS = 6
MAX_JOB_SECONDS = 1800
MAX_CLONE_MB = 500
MAX_ISSUE_URL_LENGTH = 2048
TOKEN_BUDGET_PER_JOB = 120_000
# Groq free tier: 100k tokens/day per organisation. The global daily job
# ceiling is deliberately conservative until real token-per-job numbers
# exist from Phase 3 fixture runs.
DAILY_JOB_CEILING = 3
PER_IP_DAILY_CEILING = 2

# D8 as amended 2026-11-03: Bedrock is primary on Activate credits,
# Groq free stays as fallback. Model ids come from the environment:
# the Phase 3 fixture suite arbitrates Haiku 5.5 vs Qwen3-Coder and
# the winner is recorded here, so no model id is invented in code.
LLM_PROVIDER = _os.environ.get("PATCHPILOT_LLM_PROVIDER", "bedrock")
BEDROCK_MODEL_ID = _os.environ.get("PATCHPILOT_BEDROCK_MODEL_ID", "")
GROQ_MODEL = _os.environ.get("PATCHPILOT_GROQ_MODEL", "llama-3.3-70b-versatile")

# Pinned base images per stack (major-version tags; digest pinning is
# a Phase 5 hardening item, recorded in the progress file).
PYTHON_IMAGE = "python:3.12-slim"
NODE_IMAGE = "node:22-slim"
CPP_IMAGE = "gcc:13"
RUN_CPUS = "1"
RUN_MEMORY = "512m"
RUN_TIMEOUT_SECONDS = 300
MAX_LOG_CHARS = 20000
# LLM prompts carry a windowed excerpt of the issue body, never the
# whole thing: a pathological body must not blow the context window
# on the first call. The analyzer still reads the full body.
MAX_PROMPT_ISSUE_CHARS = 6000

SERVICE_NAME = "patchpilot-agent"
SERVICE_VERSION = "0.1.0"


def job_dir() -> str:
    return _os.environ.get("PATCHPILOT_JOB_DIR", "data/jobs")
