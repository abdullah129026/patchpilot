"""Deterministic verdict engine (Phase 0, ADR-003).

Verdicts are computed from run evidence only: exit codes, signature
matches, and pipeline stop reasons. The LLM never writes a verdict.
Precedence is deliberate: a job that failed to set up did not reproduce
anything, and a job stopped by a ceiling says so instead of claiming a
result it never reached.
"""

from enum import StrEnum


class Verdict(StrEnum):
    REPRODUCED = "REPRODUCED"
    NOT_REPRODUCED = "NOT_REPRODUCED"
    SETUP_FAILED = "SETUP_FAILED"
    ISSUE_UNDERSPECIFIED = "ISSUE_UNDERSPECIFIED"
    LIMIT_REACHED = "LIMIT_REACHED"


def signature_in_log(signature: str, log: str) -> bool:
    signature = signature.strip()
    if not signature:
        return False
    return signature in log


def compute_verdict(
    exit_code: int | None,
    signature_found: bool,
    setup_failed: bool = False,
    limit_reached: bool = False,
    underspecified: bool = False,
) -> Verdict:
    if setup_failed:
        return Verdict.SETUP_FAILED
    if limit_reached:
        return Verdict.LIMIT_REACHED
    if underspecified:
        return Verdict.ISSUE_UNDERSPECIFIED
    if exit_code is not None and exit_code != 0 and signature_found:
        return Verdict.REPRODUCED
    return Verdict.NOT_REPRODUCED
