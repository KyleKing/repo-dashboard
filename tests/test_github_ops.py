import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from repo_dashboard.github_ops import _get_checks_status, get_pr_for_branch
from repo_dashboard.vcs_git import GitOperations


def test_get_pr_for_branch_returns_none_on_failure() -> None:
    result = CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    with (
        patch("repo_dashboard.github_ops.subprocess.run", return_value=result),
        patch(
            "repo_dashboard.github_ops.get_vcs_operations",
            return_value=GitOperations(),
        ),
    ):
        pr = get_pr_for_branch(Path("/repo"), "main")
        assert pr is None


def test_get_pr_for_branch_returns_none_on_invalid_json() -> None:
    result = CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
    with (
        patch("repo_dashboard.github_ops.subprocess.run", return_value=result),
        patch(
            "repo_dashboard.github_ops.get_vcs_operations",
            return_value=GitOperations(),
        ),
    ):
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
    with (
        patch("repo_dashboard.github_ops.subprocess.run", return_value=result),
        patch(
            "repo_dashboard.github_ops.get_vcs_operations",
            return_value=GitOperations(),
        ),
    ):
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
    with (
        patch("repo_dashboard.github_ops.subprocess.run", return_value=result),
        patch(
            "repo_dashboard.github_ops.get_vcs_operations",
            return_value=GitOperations(),
        ),
    ):
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


def test_get_workflow_runs_for_commit_returns_none_on_failure() -> None:
    import asyncio
    from unittest.mock import AsyncMock, patch

    from repo_dashboard.github_ops import get_workflow_runs_for_commit

    async def run_test():
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))

        with (
            patch(
                "repo_dashboard.github_ops.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch(
                "repo_dashboard.github_ops.get_vcs_operations",
                return_value=GitOperations(),
            ),
        ):
            result = await get_workflow_runs_for_commit(Path("/repo"), "abc123")
            assert result is None

    asyncio.run(run_test())


def test_get_workflow_runs_for_commit_returns_none_on_invalid_json() -> None:
    import asyncio
    from unittest.mock import AsyncMock, patch

    from repo_dashboard.github_ops import get_workflow_runs_for_commit

    async def run_test():
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"not json", b""))

        with (
            patch(
                "repo_dashboard.github_ops.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch(
                "repo_dashboard.github_ops.get_vcs_operations",
                return_value=GitOperations(),
            ),
        ):
            result = await get_workflow_runs_for_commit(Path("/repo"), "abc123")
            assert result is None

    asyncio.run(run_test())


def test_get_workflow_runs_for_commit_returns_summary() -> None:
    import asyncio
    from unittest.mock import AsyncMock, patch

    from repo_dashboard.github_ops import get_workflow_runs_for_commit

    async def run_test():
        workflow_data = [
            {
                "status": "completed",
                "conclusion": "success",
                "headSha": "abc123",
                "workflowName": "CI",
                "databaseId": 1,
                "createdAt": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner/repo/actions/runs/1",
            },
            {
                "status": "completed",
                "conclusion": "failure",
                "headSha": "abc123",
                "workflowName": "Tests",
                "databaseId": 2,
                "createdAt": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner/repo/actions/runs/2",
            },
            {
                "status": "completed",
                "conclusion": "skipped",
                "headSha": "abc123",
                "workflowName": "Deploy",
                "databaseId": 3,
                "createdAt": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner/repo/actions/runs/3",
            },
            {
                "status": "in_progress",
                "conclusion": None,
                "headSha": "abc123",
                "workflowName": "Build",
                "databaseId": 4,
                "createdAt": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner/repo/actions/runs/4",
            },
        ]

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(json.dumps(workflow_data).encode(), b"")
        )

        with (
            patch(
                "repo_dashboard.github_ops.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch(
                "repo_dashboard.github_ops.get_vcs_operations",
                return_value=GitOperations(),
            ),
        ):
            result = await get_workflow_runs_for_commit(Path("/repo"), "abc123")
            assert result is not None
            assert result.success_count == 1
            assert result.failure_count == 1
            assert result.skipped_count == 1
            assert result.pending_count == 1
            assert len(result.runs) == 4
            assert result.runs[0].workflow_name == "CI"
            assert result.runs[0].conclusion == "success"
            assert result.status_display == "✓1 ✗1 ○1 ◷1"

    asyncio.run(run_test())
