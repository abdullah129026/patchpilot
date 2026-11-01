from app.verdicts import Verdict, compute_verdict, signature_in_log


def test_reproduced_needs_nonzero_exit_and_signature():
    assert compute_verdict(exit_code=1, signature_found=True) == Verdict.REPRODUCED


def test_nonzero_exit_without_signature_is_not_reproduced():
    assert compute_verdict(exit_code=1, signature_found=False) == Verdict.NOT_REPRODUCED


def test_zero_exit_is_not_reproduced():
    assert compute_verdict(exit_code=0, signature_found=True) == Verdict.NOT_REPRODUCED


def test_setup_failure_beats_other_signals():
    assert (
        compute_verdict(exit_code=1, signature_found=True, setup_failed=True)
        == Verdict.SETUP_FAILED
    )


def test_limit_reached_beats_reproduction_signals():
    assert (
        compute_verdict(exit_code=1, signature_found=True, limit_reached=True)
        == Verdict.LIMIT_REACHED
    )


def test_signature_match_is_substring_of_log():
    log = "Traceback (most recent call last):\nValueError: bad key\n"
    assert signature_in_log("ValueError: bad key", log) is True
    assert signature_in_log("KeyError: missing", log) is False
    assert signature_in_log("", log) is False
    assert signature_in_log("   ", log) is False
