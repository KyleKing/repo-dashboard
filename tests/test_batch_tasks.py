from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from repo_dashboard.batch_tasks import BatchTaskRunner, task_fetch_all
from repo_dashboard.models import RepoStatus, RepoSummary


def _make_summary(path: Path, name: str) -> RepoSummary:
    return RepoSummary(
        path=path,
        name=name,
        vcs_type="git",
        current_branch="main",
        ahead_count=0,
        behind_count=0,
        uncommitted_count=0,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.OK,
    )


@pytest.mark.asyncio
async def test_batch_task_runner_success(tmp_path: Path) -> None:
    """Test batch task runner with successful operations"""
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    summaries = [
        _make_summary(repo1, "repo1"),
        _make_summary(repo2, "repo2"),
    ]

    async def mock_task(vcs_ops, repo_path):
        return (True, "Success")

    runner = BatchTaskRunner(summaries)

    with patch(
        "repo_dashboard.batch_tasks.get_vcs_operations"
    ) as mock_get_vcs:
        mock_vcs = AsyncMock()
        mock_get_vcs.return_value = mock_vcs

        results = await runner.run_task(mock_task)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.message == "Success" for r in results)
        assert all(r.duration_ms >= 0 for r in results)


@pytest.mark.asyncio
async def test_batch_task_runner_failure(tmp_path: Path) -> None:
    """Test batch task runner with failed operations"""
    repo1 = tmp_path / "repo1"
    repo1.mkdir()

    summaries = [_make_summary(repo1, "repo1")]

    async def mock_task(vcs_ops, repo_path):
        return (False, "Operation failed")

    runner = BatchTaskRunner(summaries)

    with patch(
        "repo_dashboard.batch_tasks.get_vcs_operations"
    ) as mock_get_vcs:
        mock_vcs = AsyncMock()
        mock_get_vcs.return_value = mock_vcs

        results = await runner.run_task(mock_task)

        assert len(results) == 1
        assert not results[0].success
        assert "Operation failed" in results[0].message


@pytest.mark.asyncio
async def test_batch_task_runner_exception(tmp_path: Path) -> None:
    """Test batch task runner handles exceptions"""
    repo1 = tmp_path / "repo1"
    repo1.mkdir()

    summaries = [_make_summary(repo1, "repo1")]

    async def mock_task(vcs_ops, repo_path):
        raise ValueError("Test error")

    runner = BatchTaskRunner(summaries)

    with patch(
        "repo_dashboard.batch_tasks.get_vcs_operations"
    ) as mock_get_vcs:
        mock_vcs = AsyncMock()
        mock_get_vcs.return_value = mock_vcs

        results = await runner.run_task(mock_task)

        assert len(results) == 1
        assert not results[0].success
        assert "Error: Test error" in results[0].message


@pytest.mark.asyncio
async def test_task_fetch_all(tmp_path: Path) -> None:
    """Test fetch_all task function"""
    repo = tmp_path / "repo"
    repo.mkdir()

    mock_vcs = AsyncMock()
    mock_vcs.fetch_all = AsyncMock(return_value=(True, "Fetched successfully"))

    success, message = await task_fetch_all(mock_vcs, repo)

    assert success is True
    assert "Fetched successfully" in message
    mock_vcs.fetch_all.assert_called_once_with(repo)
