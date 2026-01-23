import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from repo_dashboard.git_ops import get_repo_summary_async
from repo_dashboard.models import RepoStatus


@pytest.mark.asyncio
async def test_get_repo_summary_async_detached_head_sets_status() -> None:
    """Test that detached HEAD state is detected and sets appropriate status"""
    with (
        patch("repo_dashboard.git_ops.get_current_branch_async", return_value="HEAD"),
        patch("repo_dashboard.git_ops._is_detached_head_async", return_value=True),
        patch("repo_dashboard.git_ops._get_ahead_behind_async", return_value=(0, 0)),
        patch("repo_dashboard.git_ops._get_uncommitted_count_async", return_value=0),
        patch("repo_dashboard.git_ops.get_last_modified_time", return_value=datetime.now()),
        patch("repo_dashboard.git_ops.get_stash_count", return_value=0),
        patch("repo_dashboard.git_ops.get_worktree_count", return_value=0),
    ):
        result = await get_repo_summary_async(Path("/repo"))
        assert result.status == RepoStatus.DETACHED_HEAD
        assert result.warning_message == "Detached HEAD state"


@pytest.mark.asyncio
async def test_get_repo_summary_async_no_upstream_sets_status() -> None:
    """Test that repos without upstream tracking are detected"""
    with (
        patch("repo_dashboard.git_ops.get_current_branch_async", return_value="main"),
        patch("repo_dashboard.git_ops._is_detached_head_async", return_value=False),
        patch("repo_dashboard.git_ops._get_ahead_behind_async", return_value=(0, 0)),
        patch("repo_dashboard.git_ops._get_uncommitted_count_async", return_value=0),
        patch("repo_dashboard.git_ops.get_last_modified_time", return_value=datetime.now()),
        patch("repo_dashboard.git_ops.get_stash_count", return_value=0),
        patch("repo_dashboard.git_ops.get_worktree_count", return_value=0),
        patch("repo_dashboard.git_ops._get_tracking_branch", return_value=None),
    ):
        result = await get_repo_summary_async(Path("/repo"))
        assert result.status == RepoStatus.NO_UPSTREAM
        assert result.warning_message == "No upstream configured"


@pytest.mark.asyncio
async def test_get_repo_summary_async_with_upstream_is_ok() -> None:
    """Test that repos with upstream tracking have OK status"""
    with (
        patch("repo_dashboard.git_ops.get_current_branch_async", return_value="main"),
        patch("repo_dashboard.git_ops._is_detached_head_async", return_value=False),
        patch("repo_dashboard.git_ops._get_ahead_behind_async", return_value=(0, 0)),
        patch("repo_dashboard.git_ops._get_uncommitted_count_async", return_value=0),
        patch("repo_dashboard.git_ops.get_last_modified_time", return_value=datetime.now()),
        patch("repo_dashboard.git_ops.get_stash_count", return_value=0),
        patch("repo_dashboard.git_ops.get_worktree_count", return_value=0),
        patch("repo_dashboard.git_ops._get_tracking_branch", return_value="origin/main"),
    ):
        result = await get_repo_summary_async(Path("/repo"))
        assert result.status == RepoStatus.OK
        assert result.warning_message is None


@pytest.mark.asyncio
async def test_get_repo_summary_async_ahead_behind_is_ok() -> None:
    """Test that repos with ahead/behind don't check upstream"""
    with (
        patch("repo_dashboard.git_ops.get_current_branch_async", return_value="main"),
        patch("repo_dashboard.git_ops._is_detached_head_async", return_value=False),
        patch("repo_dashboard.git_ops._get_ahead_behind_async", return_value=(2, 1)),
        patch("repo_dashboard.git_ops._get_uncommitted_count_async", return_value=0),
        patch("repo_dashboard.git_ops.get_last_modified_time", return_value=datetime.now()),
        patch("repo_dashboard.git_ops.get_stash_count", return_value=0),
        patch("repo_dashboard.git_ops.get_worktree_count", return_value=0),
    ):
        result = await get_repo_summary_async(Path("/repo"))
        assert result.status == RepoStatus.OK
        assert result.ahead_count == 2
        assert result.behind_count == 1


@pytest.mark.asyncio
async def test_get_repo_summary_async_missing_git_sets_no_git_status() -> None:
    """Test that FileNotFoundError results in NO_GIT status"""
    with patch(
        "repo_dashboard.git_ops.get_current_branch_async",
        side_effect=FileNotFoundError("git not found"),
    ):
        result = await get_repo_summary_async(Path("/repo"))
        assert result.status == RepoStatus.NO_GIT
        assert result.warning_message == "Git not installed"
        assert result.current_branch == "?"


@pytest.mark.asyncio
async def test_get_repo_summary_async_other_error_sets_warning_status() -> None:
    """Test that other exceptions result in WARNING status"""
    with patch(
        "repo_dashboard.git_ops.get_current_branch_async",
        side_effect=RuntimeError("unknown error"),
    ):
        result = await get_repo_summary_async(Path("/repo"))
        assert result.status == RepoStatus.WARNING
        assert result.warning_message == "Unknown issue"
        assert result.current_branch == "?"
