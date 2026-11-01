"""Parse and validate a submitted GitHub issue URL.

Only public github.com issue URLs are accepted in v1. Everything else
is refused with a plain reason, before any fetch or clone is attempted.
The URL is data, never an instruction, and it never reaches a shell.
"""

import re
from urllib.parse import urlparse

from app.config import MAX_ISSUE_URL_LENGTH

_OWNER_REPO = re.compile(r"^[A-Za-z0-9_.-]+$")
_ISSUE_PATH = re.compile(r"^/([^/]+)/([^/]+)/issues/(\d+)/?$")


def parse_issue_url(url: str) -> tuple[str, str, int]:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("issue URL is required")
    if len(url) > MAX_ISSUE_URL_LENGTH:
        raise ValueError("issue URL is too long")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError("only https://github.com issue URLs are accepted")
    match = _ISSUE_PATH.match(parsed.path or "")
    if not match:
        raise ValueError("expected a github.com/<owner>/<repo>/issues/<number> URL")
    owner, repo, number = match.groups()
    if not _OWNER_REPO.match(owner) or not _OWNER_REPO.match(repo):
        raise ValueError("invalid owner or repo name in issue URL")
    return owner, repo, int(number)
