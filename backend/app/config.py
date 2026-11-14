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
PYTHON_IMAGE = "python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b"
NODE_IMAGE = "node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee"
CPP_IMAGE = (
    "gcc:13@sha256:8c0fe724784c6d617cb582f79ddaf5dd2233aaba2fb7a14e0b9d03348fea8088"
)
RUN_CPUS = "1"
RUN_MEMORY = "512m"
RUN_TIMEOUT_SECONDS = 300
MAX_LOG_CHARS = 20000
# LLM prompts carry a windowed excerpt of the issue body, never the
# whole thing: a pathological body must not blow the context window
# on the first call. The analyzer still reads the full body.
MAX_PROMPT_ISSUE_CHARS = 6000
# Attempts 2-6 are told what the previous attempt did (exit code and
# the tail of its log), so the model stops repeating the same failed
# script. The tail is capped for the same reason as the issue excerpt:
# a pathological log must not blow the context window on a retry.
MAX_PROMPT_LOG_TAIL_CHARS = 2000

SERVICE_NAME = "patchpilot-agent"
SERVICE_VERSION = "0.1.0"


def job_dir() -> str:
    return _os.environ.get("PATCHPILOT_JOB_DIR", "data/jobs")
