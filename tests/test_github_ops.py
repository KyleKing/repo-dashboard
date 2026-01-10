import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from multi_repo_view.github_ops import _get_checks_status, get_pr_for_branch


class TestGetPRForBranch:
    def test_returns_none_on_failure(self) -> None:
        result = CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        with patch("multi_repo_view.github_ops.subprocess.run", return_value=result):
            pr = get_pr_for_branch(Path("/repo"), "main")
            assert pr is None

    def test_returns_none_on_invalid_json(self) -> None:
        result = CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        with patch("multi_repo_view.github_ops.subprocess.run", return_value=result):
            pr = get_pr_for_branch(Path("/repo"), "main")
            assert pr is None

    def test_parses_pr_info(self) -> None:
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
        with patch("multi_repo_view.github_ops.subprocess.run", return_value=result):
            pr = get_pr_for_branch(Path("/repo"), "main")
            assert pr is not None
            assert pr.number == 123
            assert pr.title == "Add feature"
            assert pr.url == "https://github.com/user/repo/pull/123"
            assert pr.state == "OPEN"
            assert pr.checks_status == "passing"

    def test_handles_no_status_checks(self) -> None:
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
        with patch("multi_repo_view.github_ops.subprocess.run", return_value=result):
            pr = get_pr_for_branch(Path("/repo"), "feature")
            assert pr is not None
            assert pr.checks_status is None


class TestGetChecksStatus:
    def test_none_rollup_returns_none(self) -> None:
        assert _get_checks_status(None) is None

    def test_empty_rollup_returns_none(self) -> None:
        assert _get_checks_status([]) is None

    def test_all_success_returns_passing(self) -> None:
        checks = [{"conclusion": "SUCCESS"}, {"conclusion": "COMPLETED"}]
        assert _get_checks_status(checks) == "passing"

    def test_any_failure_returns_failing(self) -> None:
        checks = [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]
        assert _get_checks_status(checks) == "failing"

    def test_any_error_returns_failing(self) -> None:
        checks = [{"conclusion": "SUCCESS"}, {"conclusion": "ERROR"}]
        assert _get_checks_status(checks) == "failing"

    def test_pending_returns_pending(self) -> None:
        checks = [{"conclusion": "SUCCESS"}, {"state": "PENDING"}]
        assert _get_checks_status(checks) == "pending"

    def test_in_progress_returns_pending(self) -> None:
        checks = [{"state": "IN_PROGRESS"}]
        assert _get_checks_status(checks) == "pending"

    def test_queued_returns_pending(self) -> None:
        checks = [{"state": "QUEUED"}]
        assert _get_checks_status(checks) == "pending"

    def test_unknown_status_returns_unknown(self) -> None:
        checks = [{"conclusion": "SKIPPED"}]
        assert _get_checks_status(checks) == "unknown"
