import pytest

from app.github_url import parse_issue_url


def test_parses_plain_issue_url():
    owner, repo, number = parse_issue_url("https://github.com/psf/requests/issues/1234")
    assert (owner, repo, number) == ("psf", "requests", 1234)


def test_parses_trailing_slash():
    assert parse_issue_url("https://github.com/a/b/issues/7/") == ("a", "b", 7)


def test_rejects_non_github_host():
    with pytest.raises(ValueError):
        parse_issue_url("https://gitlab.com/a/b/issues/7")


def test_rejects_pull_request_url():
    with pytest.raises(ValueError):
        parse_issue_url("https://github.com/a/b/pull/7")


def test_rejects_issue_list_url_without_number():
    with pytest.raises(ValueError):
        parse_issue_url("https://github.com/a/b/issues")


def test_rejects_http_scheme():
    with pytest.raises(ValueError):
        parse_issue_url("http://github.com/a/b/issues/7")


def test_rejects_non_numeric_issue():
    with pytest.raises(ValueError):
        parse_issue_url("https://github.com/a/b/issues/abc")


def test_rejects_empty_and_oversized_input():
    with pytest.raises(ValueError):
        parse_issue_url("")
    with pytest.raises(ValueError):
        parse_issue_url("https://github.com/a/b/issues/1" + "x" * 3000)
