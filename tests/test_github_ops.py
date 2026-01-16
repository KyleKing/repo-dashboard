import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from repo_dashboard.github_ops import _get_checks_status, get_pr_for_branch


def test_get_pr_for_branch_returns_none_on_failure() -> None:
    result = CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    with patch("repo_dashboard.github_ops.subprocess.run", return_value=result):
        pr = get_pr_for_branch(Path("/repo"), "main")
        assert pr is None


def test_get_pr_for_branch_returns_none_on_invalid_json() -> None:
    result = CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
    with patch("repo_dashboard.github_ops.subprocess.run", return_value=result):
        pr = get_pr_for_branch(Path("/repo"), "main")
        assert pr is None


def test_get_pr_for_branch_parses_pr_info() -> None:
    pr_data = {
        "number": 123,
        "title": "Add feature",
        "url": "https://github.com/user/repo/pull/123",
        "state": "OPEN",
        "statusCheckRollup": [{"conclusion": "SUCCESS"}],
    }
    result = CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(pr_data), stderr=""
    )
    with patch("repo_dashboard.github_ops.subprocess.run", return_value=result):
        pr = get_pr_for_branch(Path("/repo"), "main")
        assert pr is not None
        assert pr.number == 123
        assert pr.title == "Add feature"
        assert pr.url == "https://github.com/user/repo/pull/123"
        assert pr.state == "OPEN"
        assert pr.checks_status == "passing"


def test_get_pr_for_branch_handles_no_status_checks() -> None:
    pr_data = {
        "number": 456,
        "title": "Simple PR",
        "url": "https://github.com/user/repo/pull/456",
        "state": "MERGED",
        "statusCheckRollup": None,
    }
    result = CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(pr_data), stderr=""
    )
    with patch("repo_dashboard.github_ops.subprocess.run", return_value=result):
        pr = get_pr_for_branch(Path("/repo"), "feature")
        assert pr is not None
        assert pr.checks_status is None


def test_get_checks_status_none_rollup_returns_none() -> None:
    assert _get_checks_status(None) is None


def test_get_checks_status_empty_rollup_returns_none() -> None:
    assert _get_checks_status([]) is None


def test_get_checks_status_all_success_returns_passing() -> None:
    checks = [{"conclusion": "SUCCESS"}, {"conclusion": "COMPLETED"}]
    assert _get_checks_status(checks) == "passing"


def test_get_checks_status_any_failure_returns_failing() -> None:
    checks = [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]
    assert _get_checks_status(checks) == "failing"


def test_get_checks_status_any_error_returns_failing() -> None:
    checks = [{"conclusion": "SUCCESS"}, {"conclusion": "ERROR"}]
    assert _get_checks_status(checks) == "failing"


def test_get_checks_status_pending_returns_pending() -> None:
    checks = [{"conclusion": "SUCCESS"}, {"state": "PENDING"}]
    assert _get_checks_status(checks) == "pending"


def test_get_checks_status_in_progress_returns_pending() -> None:
    checks = [{"state": "IN_PROGRESS"}]
    assert _get_checks_status(checks) == "pending"


def test_get_checks_status_queued_returns_pending() -> None:
    checks = [{"state": "QUEUED"}]
    assert _get_checks_status(checks) == "pending"


def test_get_checks_status_unknown_status_returns_unknown() -> None:
    checks = [{"conclusion": "SKIPPED"}]
    assert _get_checks_status(checks) == "unknown"
