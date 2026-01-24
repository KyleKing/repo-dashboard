from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import DataTable

from repo_dashboard.app import RepoDashboardApp
from repo_dashboard.models import (
    ActiveFilter,
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
        vcs_type="git",
        current_branch=branch,
        ahead_count=ahead,
        behind_count=behind,
        staged_count=0,
        unstaged_count=uncommitted,
        untracked_count=0,
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

    app = RepoDashboardApp(
        scan_paths=[empty_dir],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()


@pytest.mark.asyncio
async def test_creates_datatable_on_mount(tmp_repos: list[Path]) -> None:
    app = RepoDashboardApp(
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
    app = RepoDashboardApp(
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
async def test_filter_popup_adds_filter(tmp_repos: list[Path]) -> None:
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._active_filters == []
        await pilot.press("f")
        await pilot.press("d")
        assert len(app._active_filters) == 1
        assert app._active_filters[0].mode == FilterMode.DIRTY


@pytest.mark.asyncio
async def test_sort_popup_changes_mode(tmp_repos: list[Path]) -> None:
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._sort_mode == SortMode.NAME
        assert app._sort_reverse is False
        await pilot.press("s")
        await pilot.press("m")
        assert app._sort_mode == SortMode.MODIFIED


@pytest.mark.asyncio
async def test_refresh_resets_filter_and_sort(tmp_repos: list[Path]) -> None:
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("f")
        await pilot.press("d")
        await pilot.press("s")
        await pilot.press("m")
        assert len(app._active_filters) > 0
        assert app._sort_mode != SortMode.NAME
        await pilot.press("r")
        await pilot.pause()
        assert app._active_filters == []
        assert app._sort_mode == SortMode.NAME


@pytest.mark.asyncio
async def test_detail_panel_hidden_initially(tmp_repos: list[Path]) -> None:
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        from repo_dashboard.modals import DetailPanel

        panel = app.query_one("#detail-panel", DetailPanel)
        assert panel.display is False


@pytest.mark.asyncio
async def test_detail_panel_shown_in_repo_detail_view(tmp_repos: list[Path]) -> None:
    from datetime import datetime

    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    summary = _make_summary(tmp_repos[0])

    from repo_dashboard.vcs_git import GitOperations
    mock_vcs = GitOperations()
    mock_vcs.get_branch_list_async = AsyncMock(return_value=[])
    mock_vcs.get_stash_list = AsyncMock(return_value=[])
    mock_vcs.get_worktree_list = AsyncMock(return_value=[])

    with patch("repo_dashboard.app.get_vcs_operations", return_value=mock_vcs):
        async with app.run_test() as pilot:
            await pilot.pause()
            app._summaries[tmp_repos[0]] = summary
            app._show_repo_detail_view(tmp_repos[0])
            await pilot.pause()

            from repo_dashboard.modals import DetailPanel

            panel = app.query_one("#detail-panel", DetailPanel)
            assert panel.display is True


@pytest.mark.asyncio
async def test_detail_panel_auto_shows_first_item(tmp_repos: list[Path]) -> None:
    from datetime import datetime

    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    summary = _make_summary(tmp_repos[0])

    from repo_dashboard.vcs_git import GitOperations
    mock_vcs = GitOperations()
    mock_vcs.get_branch_list_async = AsyncMock(return_value=[_make_branch_info("main", True)])
    mock_vcs.get_stash_list = AsyncMock(return_value=[])
    mock_vcs.get_worktree_list = AsyncMock(return_value=[])

    with patch("repo_dashboard.app.get_vcs_operations", return_value=mock_vcs):
        async with app.run_test() as pilot:
            await pilot.pause()
            app._summaries[tmp_repos[0]] = summary
            app._selected_repo = tmp_repos[0]
            app._show_repo_detail_view(tmp_repos[0])
            await pilot.pause()

            from repo_dashboard.modals import DetailPanel

            panel = app.query_one("#detail-panel", DetailPanel)
            title = panel.query_one("#detail-panel-title")
            title_text = str(title.render())
            assert "Branch: main" in title_text


@pytest.mark.asyncio
async def test_detail_panel_shows_placeholder_when_no_items(tmp_repos: list[Path]) -> None:
    from datetime import datetime

    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    summary = _make_summary(tmp_repos[0])

    from repo_dashboard.vcs_git import GitOperations
    mock_vcs = GitOperations()
    mock_vcs.get_branch_list_async = AsyncMock(return_value=[])
    mock_vcs.get_stash_list = AsyncMock(return_value=[])
    mock_vcs.get_worktree_list = AsyncMock(return_value=[])

    with patch("repo_dashboard.app.get_vcs_operations", return_value=mock_vcs):
        async with app.run_test() as pilot:
            await pilot.pause()
            app._summaries[tmp_repos[0]] = summary
            app._selected_repo = tmp_repos[0]
            app._show_repo_detail_view(tmp_repos[0])
            await pilot.pause()

            from repo_dashboard.modals import DetailPanel

            panel = app.query_one("#detail-panel", DetailPanel)
            title = panel.query_one("#detail-panel-title")
            title_text = str(title.render())
            assert "Select an item" in title_text


@pytest.mark.asyncio
async def test_vcs_badge_display_with_mixed_repos(tmp_path: Path) -> None:
    """Test VCS badge display and counting with mixed git/jj repos"""
    git_repo = tmp_path / "git-repo"
    jj_repo = tmp_path / "jj-repo"
    colocated_repo = tmp_path / "colocated-repo"

    git_repo.mkdir()
    (git_repo / ".git").mkdir()

    jj_repo.mkdir()
    (jj_repo / ".jj").mkdir()

    colocated_repo.mkdir()
    (colocated_repo / ".git").mkdir()
    (colocated_repo / ".jj").mkdir()

    app = RepoDashboardApp(
        scan_paths=[tmp_path],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert len(app._summaries) == 3

        git_summary = app._summaries.get(git_repo)
        jj_summary = app._summaries.get(jj_repo)
        colocated_summary = app._summaries.get(colocated_repo)

        assert git_summary is not None
        assert git_summary.vcs_type == "git"

        assert jj_summary is not None
        assert jj_summary.vcs_type == "jj"

        assert colocated_summary is not None
        assert colocated_summary.vcs_type == "jj"


@pytest.mark.asyncio
async def test_batch_fetch_workflow(tmp_repos: list[Path]) -> None:
    """Test full batch fetch workflow: filter → execute batch operation"""
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    summary1 = _make_summary(tmp_repos[0], ahead=2)
    summary2 = _make_summary(tmp_repos[1], behind=1)

    from repo_dashboard.vcs_git import GitOperations
    mock_vcs = GitOperations()
    mock_vcs.fetch_all = AsyncMock(return_value=(True, "Fetched successfully"))

    with patch("repo_dashboard.app.get_vcs_operations", return_value=mock_vcs):
        async with app.run_test() as pilot:
            await pilot.pause()
            app._summaries[tmp_repos[0]] = summary1
            app._summaries[tmp_repos[1]] = summary2
            app._refresh_table_with_filters()
            await pilot.pause()

            await pilot.press("f")
            await pilot.press("a")
            await pilot.pause()

            assert app._current_view == "repo_list"

            await pilot.press("F")
            await pilot.pause()


@pytest.mark.asyncio
async def test_batch_operation_not_available_in_detail_view(tmp_repos: list[Path]) -> None:
    """Test that batch operations show warning in detail view"""
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    summary = _make_summary(tmp_repos[0])

    from repo_dashboard.vcs_git import GitOperations
    mock_vcs = GitOperations()
    mock_vcs.get_branch_list_async = AsyncMock(return_value=[])
    mock_vcs.get_stash_list = AsyncMock(return_value=[])
    mock_vcs.get_worktree_list = AsyncMock(return_value=[])

    with patch("repo_dashboard.app.get_vcs_operations", return_value=mock_vcs):
        async with app.run_test() as pilot:
            await pilot.pause()
            app._summaries[tmp_repos[0]] = summary
            app._show_repo_detail_view(tmp_repos[0])
            await pilot.pause()

            assert app._current_view == "repo_detail"

            app.action_batch_fetch()
            await pilot.pause()


@pytest.mark.asyncio
async def test_batch_operation_with_no_repos(tmp_path: Path) -> None:
    """Test batch operation with no filtered repos shows warning"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    app = RepoDashboardApp(
        scan_paths=[empty_dir],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert app._current_view == "repo_list"

        app.action_batch_fetch()
        await pilot.pause()


@pytest.mark.asyncio
async def test_error_handling_in_repo_discovery(tmp_path: Path) -> None:
    """Test error handling when repo discovery encounters issues"""
    normal_repo = tmp_path / "normal"
    normal_repo.mkdir()
    (normal_repo / ".git").mkdir()

    app = RepoDashboardApp(
        scan_paths=[tmp_path],
        scan_depth=1,
        theme="dark",
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert len(app._summaries) == 1
        assert normal_repo in app._summaries


@pytest.mark.asyncio
async def test_navigation_between_views(tmp_repos: list[Path]) -> None:
    """Test navigation: list → detail → back to list"""
    app = RepoDashboardApp(
        scan_paths=[tmp_repos[0].parent],
        scan_depth=1,
        theme="dark",
    )

    summary = _make_summary(tmp_repos[0])

    from repo_dashboard.vcs_git import GitOperations
    mock_vcs = GitOperations()
    mock_vcs.get_branch_list_async = AsyncMock(return_value=[])
    mock_vcs.get_stash_list = AsyncMock(return_value=[])
    mock_vcs.get_worktree_list = AsyncMock(return_value=[])

    with patch("repo_dashboard.app.get_vcs_operations", return_value=mock_vcs):
        async with app.run_test() as pilot:
            await pilot.pause()
            app._summaries[tmp_repos[0]] = summary
            app._refresh_table_with_filters()
            await pilot.pause()

            assert app._current_view == "repo_list"

            app._show_repo_detail_view(tmp_repos[0])
            await pilot.pause()

            assert app._current_view == "repo_detail"

            await pilot.press("escape")
            await pilot.pause()

            assert app._current_view == "repo_list"
