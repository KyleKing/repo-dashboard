from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import DataTable

from multi_repo_view.app import MultiRepoViewApp
from multi_repo_view.models import (
    BranchInfo,
    FilterMode,
    PRInfo,
    RepoStatus,
    RepoSummary,
    SortMode,
)


def _make_summary(
    path: Path,
    branch: str = "main",
    ahead: int = 0,
    behind: int = 0,
    uncommitted: int = 0,
) -> RepoSummary:
    return RepoSummary(
        path=path,
        name=path.name,
        current_branch=branch,
        ahead_count=ahead,
        behind_count=behind,
        uncommitted_count=uncommitted,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.OK,
    )


def _make_branch_info(name: str, is_current: bool = False) -> BranchInfo:
    return BranchInfo(
        name=name,
        is_current=is_current,
        ahead=0,
        behind=0,
        tracking=f"origin/{name}",
    )


@pytest.fixture
def tmp_repos(tmp_path: Path) -> list[Path]:
    """Create temporary git repos"""
    repo1 = tmp_path / "project-a"
    repo2 = tmp_path / "project-b"

    for repo in [repo1, repo2]:
        repo.mkdir()
        (repo / ".git").mkdir()

    return [repo1, repo2]


@pytest.mark.asyncio
async def test_shows_warning_when_no_repos(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    app = MultiRepoViewApp(
        scan_paths=[empty_dir],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()


@pytest.mark.asyncio
async def test_creates_datatable_on_mount(tmp_repos: list[Path]) -> None:
    app = MultiRepoViewApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one(DataTable)
        assert table is not None


@pytest.mark.asyncio
async def test_datatable_has_correct_columns(tmp_repos: list[Path]) -> None:
    app = MultiRepoViewApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one(DataTable)
        columns = [col.label.plain for col in table.columns.values()]
        assert any("Name" in col for col in columns)
        assert any("Branch" in col for col in columns)
        assert any("Status" in col for col in columns)


@pytest.mark.asyncio
async def test_cycle_filter_changes_mode(tmp_repos: list[Path]) -> None:
    app = MultiRepoViewApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._filter_mode == FilterMode.ALL
        await pilot.press("f")
        assert app._filter_mode == FilterMode.DIRTY
        await pilot.press("f")
        assert app._filter_mode == FilterMode.AHEAD


@pytest.mark.asyncio
async def test_cycle_sort_changes_mode(tmp_repos: list[Path]) -> None:
    app = MultiRepoViewApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._sort_mode == SortMode.NAME
        await pilot.press("s")
        assert app._sort_mode == SortMode.MODIFIED
        await pilot.press("s")
        assert app._sort_mode == SortMode.STATUS


@pytest.mark.asyncio
async def test_refresh_resets_filter_and_sort(tmp_repos: list[Path]) -> None:
    app = MultiRepoViewApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("f")
        await pilot.press("s")
        assert app._filter_mode != FilterMode.ALL
        assert app._sort_mode != SortMode.NAME
        await pilot.press("r")
        await pilot.pause()
        assert app._filter_mode == FilterMode.ALL
        assert app._sort_mode == SortMode.NAME
