"""Tests for the fixture suite runner and the curated fixture file."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

_RUNNER = Path(__file__).resolve().parents[2] / "scripts" / "run-fixture-suite.py"
_spec = importlib.util.spec_from_file_location("run_fixture_suite", _RUNNER)
_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runner)
load_entries = _runner.load_entries

FIXTURE_FILE = Path(__file__).resolve().parents[2] / "scripts" / "fixture_issues.json"
_SHA = re.compile(r"^[0-9a-f]{40}$")


def test_load_entries_rejects_missing_base_commit(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"owner": "a", "repo": "b", "number": 1}]))
    with pytest.raises(ValueError):
        load_entries(bad)


def test_checked_in_fixture_file_is_valid():
    entries = load_entries(FIXTURE_FILE)
    assert len(entries) == 10
    seen = set()
    for entry in entries:
        assert _SHA.match(entry["base_commit"])
        assert _SHA.match(entry["fix_commit"])
        assert entry["error_signature"]
        key = (entry["owner"], entry["repo"], entry["number"])
        assert key not in seen
        seen.add(key)
