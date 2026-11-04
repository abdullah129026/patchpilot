"""Issue analysis (Phase 3): error signature extraction + quality check.

The signature is the last error-shaped line in the title and body.
Deterministic matching in v1 needs that line: without it there is
nothing to match a run log against, so the pipeline stops with
ISSUE_UNDERSPECIFIED before spending any compute. Issue text is data
throughout; nothing here executes or forwards it anywhere but the
LLM prompt, where it stays quoted as the report under analysis.
"""

import re

_PATTERNS = [
    re.compile(r"^([A-Za-z_][\w.]*?(?:Error|Exception)|Error)\b.*$"),
    re.compile(r"^Segmentation fault\b.*$"),
    re.compile(r"^Assertion .* failed\b.*$"),
    re.compile(r"^terminate called\b.*$"),
]


def extract_signature(text: str) -> str | None:
    found = None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if any(pattern.match(line) for pattern in _PATTERNS):
            found = line
    return found[:300] if found else None


def analyze_issue(issue: dict) -> dict:
    text = f"{issue.get('title', '')}\n{issue.get('body', '') or ''}"
    signature = extract_signature(text)
    return {"signature": signature, "underspecified": signature is None}
