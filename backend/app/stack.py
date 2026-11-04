"""Stack detection from a cloned repo's file list (Phase 3).

Manifests win over extension counts: a repo with a pyproject.toml is
a Python repo even if it ships JavaScript examples. Anything else
returns None, and the pipeline reports SETUP_FAILED with an honest
unsupported-language reason rather than guessing a runtime.
"""

from collections import Counter
from pathlib import Path

_MANIFESTS = {
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "requirements.txt": "python",
    "package.json": "javascript",
    "CMakeLists.txt": "cpp",
    "meson.build": "cpp",
}

_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
}


def detect(files) -> str | None:
    names = {Path(f).name for f in files}
    for manifest, stack in _MANIFESTS.items():
        if manifest in names:
            return stack
    counts = Counter(
        _EXTENSIONS[Path(f).suffix] for f in files if Path(f).suffix in _EXTENSIONS
    )
    if not counts:
        return None
    # .h alone is ambiguous (C or C++); it only counts with C++ siblings.
    if set(counts) == {"cpp"} and all(
        Path(f).suffix == ".h" for f in files if Path(f).suffix in _EXTENSIONS
    ):
        return None
    return counts.most_common(1)[0][0]


def list_files(root: str | Path, limit: int = 5000) -> list[str]:
    root = Path(root)
    found = []
    for path in sorted(root.rglob("*")):
        if len(found) >= limit:
            break
        if path.is_file() and ".git" not in path.parts:
            found.append(path.relative_to(root).as_posix())
    return found
