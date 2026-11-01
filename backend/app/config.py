"""Ceilings and model config, from Phase 0 sections 0.2 and 0.3.

One place for every number that stops a job. Phase 2 wires the per-IP
and global daily ceilings into the submission path; the constants land
here in Phase 1 so nothing later invents its own limit.
"""

import os

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

LLM_PROVIDER = "groq"
LLM_MODEL = "llama-3.3-70b-versatile"

SERVICE_NAME = "patchpilot-agent"
SERVICE_VERSION = "0.1.0"


def job_dir() -> str:
    return os.environ.get("PATCHPILOT_JOB_DIR", "data/jobs")
