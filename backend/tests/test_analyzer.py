from app.analyzer import analyze_issue, extract_signature


def test_python_traceback_signature_is_last_error_line():
    body = (
        "Traceback (most recent call last):\n"
        '  File "app.py", line 3, in load\n'
        "    return data[key]\n"
        "KeyError: 'missing'\n"
    )
    assert extract_signature(body) == "KeyError: 'missing'"


def test_javascript_error_line():
    assert extract_signature("TypeError: Cannot read properties of undefined") == (
        "TypeError: Cannot read properties of undefined"
    )


def test_no_error_line_gives_none():
    assert extract_signature("It crashes sometimes when I click save.") is None


def test_analyze_marks_underspecified_without_signature():
    result = analyze_issue({"title": "Crash", "body": "It crashes sometimes."})
    assert result["signature"] is None
    assert result["underspecified"] is True


def test_analyze_keeps_signature_from_title_or_body():
    result = analyze_issue(
        {
            "title": "ValueError on empty config",
            "body": "Steps: load {} and watch it fail.",
        }
    )
    assert result["signature"] == "ValueError on empty config"
    assert result["underspecified"] is False
