from pathlib import Path
from textwrap import dedent
from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import Static

from multi_repo_view.app import MultiRepoViewApp
from multi_repo_view.models import BranchInfo, PRInfo, RepoSummary
from multi_repo_view.widgets.repo_detail import RepoDetailView
from multi_repo_view.widgets.repo_list import RepoList, RepoListItem


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
def config_with_repos(tmp_path: Path) -> Path:
    repo1 = tmp_path / "project-a"
    repo2 = tmp_path / "project-b"
    repo1.mkdir()
    repo2.mkdir()
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        dedent(f"""\
        [[repos]]
        path = "{repo1}"

        [[repos]]
        path = "{repo2}"
        """)
    )
    return config_file


@pytest.fixture
def empty_config(tmp_path: Path) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text("")
    return config_file


class TestAppEmptyState:
    @pytest.mark.asyncio
    async def test_shows_empty_state_widget_when_no_repos(
        self, empty_config: Path
    ) -> None:
        app = MultiRepoViewApp(config_path=empty_config)
        async with app.run_test() as pilot:
            await pilot.pause()
            empty_state = app.query_one("#empty-state", Static)
            assert empty_state is not None

    @pytest.mark.asyncio
    async def test_no_repo_list_when_no_repos(self, empty_config: Path) -> None:
        app = MultiRepoViewApp(config_path=empty_config)
        async with app.run_test() as pilot:
            await pilot.pause()
            repo_lists = app.query(RepoList)
            assert len(repo_lists) == 0

    def test_empty_state_message_contains_guidance(self, empty_config: Path) -> None:
        app = MultiRepoViewApp(config_path=empty_config)
        message = app._get_empty_state_message()
        assert "No repositories configured" in message

    def test_empty_state_message_contains_config_path(self, empty_config: Path) -> None:
        app = MultiRepoViewApp(config_path=empty_config)
        message = app._get_empty_state_message()
        assert str(empty_config) in message

    def test_empty_state_message_contains_example(self, empty_config: Path) -> None:
        app = MultiRepoViewApp(config_path=empty_config)
        message = app._get_empty_state_message()
        assert "[[repos]]" in message


class TestAppWithRepos:
    @pytest.mark.asyncio
    async def test_shows_repo_list_when_repos_configured(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a"),
            _make_summary(tmp_path / "project-b"),
        ]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with patch(
            "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                items = repo_list.query(RepoListItem)
                assert len(items) == 2

    @pytest.mark.asyncio
    async def test_repo_list_shows_branch_names(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a", branch="main"),
            _make_summary(tmp_path / "project-b", branch="develop"),
        ]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with patch(
            "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                items = list(repo_list.query(RepoListItem))
                assert items[0].summary.current_branch == "main"
                assert items[1].summary.current_branch == "develop"

    @pytest.mark.asyncio
    async def test_repo_list_shows_status_counts(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a", ahead=2, uncommitted=3),
            _make_summary(tmp_path / "project-b", ahead=0, uncommitted=0),
        ]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with patch(
            "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                items = list(repo_list.query(RepoListItem))
                assert items[0].summary.ahead_count == 2
                assert items[0].summary.uncommitted_count == 3
                assert items[1].summary.is_dirty is False


class TestVimKeybindings:
    @pytest.mark.asyncio
    async def test_j_moves_cursor_down(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a"),
            _make_summary(tmp_path / "project-b"),
        ]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with patch(
            "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                repo_list.focus()
                repo_list.index = 0
                await pilot.press("j")
                assert repo_list.index == 1

    @pytest.mark.asyncio
    async def test_k_moves_cursor_up(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a"),
            _make_summary(tmp_path / "project-b"),
        ]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with patch(
            "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                repo_list.focus()
                repo_list.index = 1
                await pilot.press("k")
                assert repo_list.index == 0

    @pytest.mark.asyncio
    async def test_q_quits_app(self, empty_config: Path) -> None:
        app = MultiRepoViewApp(config_path=empty_config)
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert app._exit


class TestRepoSelection:
    @pytest.mark.asyncio
    async def test_selecting_repo_updates_detail_view(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a"),
            _make_summary(tmp_path / "project-b"),
        ]
        branches = [_make_branch_info("main", is_current=True)]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with (
            patch(
                "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
            ),
            patch(
                "multi_repo_view.app.get_branch_list_async",
                AsyncMock(return_value=branches),
            ),
            patch(
                "multi_repo_view.app.get_status_files_async",
                AsyncMock(return_value=([], [], [])),
            ),
            patch(
                "multi_repo_view.app.get_pr_for_branch_async",
                AsyncMock(return_value=None),
            ),
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                repo_list.focus()
                await pilot.press("enter")
                await pilot.pause()
                detail_view = app.query_one(RepoDetailView)
                assert detail_view._detail is not None
                assert detail_view._detail.summary.name == "project-a"

    @pytest.mark.asyncio
    async def test_detail_view_shows_pr_info(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a"),
            _make_summary(tmp_path / "project-b"),
        ]
        branches = [_make_branch_info("main", is_current=True)]
        pr = PRInfo(
            number=123,
            title="Add feature X",
            url="https://github.com/user/repo/pull/123",
            state="OPEN",
            checks_status="passing",
        )

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with (
            patch(
                "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
            ),
            patch(
                "multi_repo_view.app.get_branch_list_async",
                AsyncMock(return_value=branches),
            ),
            patch(
                "multi_repo_view.app.get_status_files_async",
                AsyncMock(return_value=([], [], [])),
            ),
            patch(
                "multi_repo_view.app.get_pr_for_branch_async",
                AsyncMock(return_value=pr),
            ),
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                repo_list = app.query_one(RepoList)
                repo_list.focus()
                await pilot.press("enter")
                await pilot.pause()
                detail_view = app.query_one(RepoDetailView)
                assert detail_view.pr_url == "https://github.com/user/repo/pull/123"


class TestRefreshAction:
    @pytest.mark.asyncio
    async def test_refresh_action_reloads_data(
        self, config_with_repos: Path, tmp_path: Path
    ) -> None:
        summaries = [
            _make_summary(tmp_path / "project-a"),
            _make_summary(tmp_path / "project-b"),
        ]

        async def mock_summary(path: Path) -> RepoSummary:
            for s in summaries:
                if s.path == path:
                    return s
            return summaries[0]

        with patch(
            "multi_repo_view.app.get_repo_summary_async", side_effect=mock_summary
        ):
            app = MultiRepoViewApp(config_path=config_with_repos)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("r")
                await pilot.pause()
                assert len(app._summaries) == 2
