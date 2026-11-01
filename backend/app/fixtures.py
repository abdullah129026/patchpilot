"""Fixture jobs for the Phase 1 click path.

These are synthetic examples, clearly flagged, used so the frontend and
the report shape can be built and reviewed before any real job runs.
Nothing here claims a real reproduction: the repo names are fictional.
"""

FIXTURES = [
    {
        "id": "fixture-reproduced",
        "status": "done",
        "verdict": "REPRODUCED",
        "fixture": True,
        "issue": {"owner": "fixture", "repo": "demo-python-app", "number": 42},
        "stack": "python",
        "signature": "ValueError: bad key",
        "attempts": [
            {
                "n": 1,
                "exit_code": 1,
                "log": "Traceback (most recent call last):\nValueError: bad key\n",
                "script": 'config = {}\nprint(config["missing"])\n',
            }
        ],
        "repro_script": 'config = {}\nprint(config["missing"])\n',
        "failing_test": "def test_missing_key():\n    assert load_config({}) is not None\n",
        "fix_diff": "--- a/config.py\n+++ b/config.py\n-    return data[key]\n+    return data.get(key)\n",
        "fix_verified": True,
    },
    {
        "id": "fixture-not-reproduced",
        "status": "done",
        "verdict": "NOT_REPRODUCED",
        "fixture": True,
        "issue": {"owner": "fixture", "repo": "demo-python-app", "number": 43},
        "stack": "python",
        "signature": "KeyError: missing",
        "attempts": [
            {"n": 1, "exit_code": 0, "log": "ok\n", "script": "print('ok')\n"},
        ],
        "repro_script": None,
        "failing_test": None,
        "fix_diff": None,
        "fix_verified": False,
    },
]


def get_fixture(fixture_id: str) -> dict | None:
    for fixture in FIXTURES:
        if fixture["id"] == fixture_id:
            return fixture
    return None
