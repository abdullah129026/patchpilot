"""Sample jobs served by the frontend and the fixtures endpoint.

These are real runs from the Phase 3 fixture suite (host run
fixture-qwen7, 2026-11-06, Qwen3-Coder): the issue, error signature,
and verdict are the recorded result for that issue. The reproduction
script and failing test are the recorded minimal repro from
scripts/fixture_issues.json, expressed as runnable code; the script
failed at the issue's base commit and passed at its fix commit during
fixture curation. No fix diff is shown on samples: the agent's
suggested diff from the host run is not stored locally, and an
unverified diff must never be presented as one.
"""

FIXTURES = [
    {
        "id": "sample-humanize-57",
        "status": "done",
        "verdict": "REPRODUCED",
        "fixture": True,
        "issue": {"owner": "python-humanize", "repo": "humanize", "number": 57},
        "stack": "python",
        "signature": "ValueError: math domain error",
        "attempts": [
            {
                "n": 1,
                "exit_code": 1,
                "log": "ValueError: math domain error\n",
                "script": "import humanize\n\nprint(humanize.metric(0))\n",
            }
        ],
        "repro_script": "import humanize\n\nprint(humanize.metric(0))\n",
        "failing_test": "import humanize\n\n\ndef test_metric_zero():\n    humanize.metric(0)\n",
        "fix_diff": None,
        "fix_verified": False,
    },
    {
        "id": "sample-pyflakes-764",
        "status": "done",
        "verdict": "REPRODUCED",
        "fixture": True,
        "issue": {"owner": "PyCQA", "repo": "pyflakes", "number": 764},
        "stack": "python",
        "signature": "TypeError: 'bool' object is not subscriptable",
        "attempts": [
            {
                "n": 1,
                "exit_code": 1,
                "log": "TypeError: 'bool' object is not subscriptable\n",
                "script": 'from pyflakes.api import check\n\ncheck("x: int\\nx.__dict__\\ndef f(): x = 1\\n")\n',
            }
        ],
        "repro_script": 'from pyflakes.api import check\n\ncheck("x: int\\nx.__dict__\\ndef f(): x = 1\\n")\n',
        "failing_test": 'from pyflakes.api import check\n\n\ndef test_annotated_name_lookup():\n    check("x: int\\nx.__dict__\\ndef f(): x = 1\\n")\n',
        "fix_diff": None,
        "fix_verified": False,
    },
    {
        "id": "sample-pyflakes-744",
        "status": "done",
        "verdict": "NOT_REPRODUCED",
        "fixture": True,
        "issue": {"owner": "PyCQA", "repo": "pyflakes", "number": 744},
        "stack": "python",
        "signature": "AttributeError: 'Name' object has no attribute '_pyflakes_parent'",
        "attempts": [
            {
                "n": 1,
                "exit_code": 0,
                "log": "No output contained the reported error.\n",
                "script": 'from pyflakes.api import check\n\ncheck("print *= -1\\n")\n',
            }
        ],
        "repro_script": 'from pyflakes.api import check\n\ncheck("print *= -1\\n")\n',
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
