import asyncio
import webbrowser
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Footer, Static

from multi_repo_view.cache import branch_cache, commit_cache, pr_cache
from multi_repo_view.discovery import discover_git_repos
from multi_repo_view.git_ops import (
    get_branch_list_async,
    get_repo_summary_async,
    get_stash_list,
    get_upstream_repo,
    get_worktree_list,
)
from multi_repo_view.github_ops import get_pr_for_branch_async
from multi_repo_view.modals import (
    BranchDetailModal,
    CopyPopup,
    HelpModal,
    StashDetailModal,
    WorktreeDetailModal,
)
from multi_repo_view.models import (
    BranchInfo,
    FilterMode,
    RepoStatus,
    RepoSummary,
    SortMode,
)
from multi_repo_view.utils import format_relative_time, truncate


class StatusBadge:
    """Badge configuration for status display"""

    def __init__(self, label: str, value: int | str, color: str, bg_color: str):
        self.label = label
        self.value = value
        self.color = color
        self.bg_color = bg_color

    def render(self) -> str:
        return f"[{self.color} on {self.bg_color}] {self.label}:{self.value} [/]"


class Breadcrumbs(Static):
    """Breadcrumb navigation bar with K9s-style status badges"""

    DEFAULT_CSS = """
    Breadcrumbs {
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, path: list[str]):
        super().__init__()
        self.path = path
        self.badges: list[StatusBadge] = []

    def render(self) -> str:
        crumbs = ["repos"] + self.path
        if len(crumbs) == 1:
            breadcrumb_text = f"[bold white on dodgerblue] {crumbs[0]} [/]"
        else:
            parts = []
            for i, crumb in enumerate(crumbs):
                if i == len(crumbs) - 1:
                    parts.append(f"[bold white on dodgerblue] {crumb} [/]")
                else:
                    parts.append(f"[white on grey30] {crumb} [/]")
            breadcrumb_text = " [dim]▸[/] ".join(parts)

        if self.badges:
            badge_text = " ".join(badge.render() for badge in self.badges)
            return f"{breadcrumb_text}  {badge_text}"
        return breadcrumb_text

    def update_path(self, path: list[str]) -> None:
        self.path = path
        self.refresh()

    def update_badges(self, badges: list[StatusBadge]) -> None:
        self.badges = badges
        self.refresh()


class MultiRepoViewApp(App):
    TITLE = "Multi-Repo View"

    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_pr", "Open PR"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "jump_top", "Top", show=False),
        Binding("G", "jump_bottom", "Bottom", show=False),
        Binding("space", "select", "Select", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("escape", "back", "Back", show=False),
        Binding("c", "copy", "Copy"),
        Binding("f", "cycle_filter", "Filter"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("?", "help", "Help"),
    ]

    def __init__(
        self,
        scan_paths: list[Path],
        scan_depth: int,
        theme: str,
    ) -> None:
        super().__init__()
        self.scan_paths = scan_paths
        self.scan_depth = scan_depth
        self.theme_name = theme
        self._repo_paths: list[Path] = []
        self._summaries: dict[Path, RepoSummary] = {}
        self._current_view = "repo_list"
        self._selected_repo: Path | None = None
        self._breadcrumb_path: list[str] = []
        self._filter_mode: FilterMode = FilterMode.ALL
        self._sort_mode: SortMode = SortMode.NAME
        self._filter_text: str = ""

    def compose(self) -> ComposeResult:
        yield Breadcrumbs([])
        yield Static("", id="filter-sort-status")
        with Container(id="main-container"):
            yield DataTable(id="main-table", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        if self.theme_name == "light":
            self.theme = "textual-light"
        else:
            self.theme = "textual-dark"

        self._repo_paths = discover_git_repos(self.scan_paths, self.scan_depth)

        if not self._repo_paths:
            self.notify("No git repositories found", severity="warning")
            return

        self._show_repo_list_table()
        self._start_progressive_load()

    def _show_repo_list_table(self) -> None:
        """Show repo list table"""
        table = self.query_one(DataTable)
        table.clear(columns=True)

        table.add_column("Name", width=30)
        table.add_column("Branch", width=25)
        table.add_column("Status", width=20)
        table.add_column("PR", width=45)
        table.add_column("Modified", width=15)
        table.cursor_type = "row"
        table.zebra_stripes = True

        for repo_path in self._repo_paths:
            table.add_row(
                repo_path.name,
                "...",
                "...",
                "...",
                "...",
                key=str(repo_path),
            )

        breadcrumbs = self.query_one(Breadcrumbs)
        breadcrumbs.update_path([])
        self._update_filter_sort_status()

    def _start_progressive_load(self) -> None:
        """Load repo summaries progressively"""
        for repo_path in self._repo_paths:
            self.run_worker(
                self._load_repo_summary(repo_path),
                group="summaries",
                exclusive=False,
            )

    async def _load_repo_summary(self, path: Path) -> None:
        """Load single repo summary and update table"""
        summary = await get_repo_summary_async(path)

        upstream = await get_upstream_repo(path)
        if upstream:
            cache_key = f"{upstream}:{summary.current_branch}"
            if pr_info := pr_cache.get(cache_key):
                summary = RepoSummary(
                    path=summary.path,
                    name=summary.name,
                    current_branch=summary.current_branch,
                    ahead_count=summary.ahead_count,
                    behind_count=summary.behind_count,
                    uncommitted_count=summary.uncommitted_count,
                    stash_count=summary.stash_count,
                    worktree_count=summary.worktree_count,
                    pr_info=pr_info,
                    last_modified=summary.last_modified,
                    status=summary.status,
                )
            else:
                pr_info = await get_pr_for_branch_async(path, summary.current_branch)
                if pr_info:
                    pr_cache.set(cache_key, pr_info)
                    summary = RepoSummary(
                        path=summary.path,
                        name=summary.name,
                        current_branch=summary.current_branch,
                        ahead_count=summary.ahead_count,
                        behind_count=summary.behind_count,
                        uncommitted_count=summary.uncommitted_count,
                        stash_count=summary.stash_count,
                        worktree_count=summary.worktree_count,
                        pr_info=pr_info,
                        last_modified=summary.last_modified,
                        status=summary.status,
                    )

        self._summaries[path] = summary
        self._update_repo_table_row(path, summary)

    def _refresh_table_with_filters(self) -> None:
        from multi_repo_view.filters import filter_repos, sort_repos

        if self._current_view != "repo_list":
            return

        filtered = filter_repos(self._summaries, self._filter_mode, self._filter_text)
        sorted_paths = sort_repos(list(filtered.keys()), filtered, self._sort_mode)

        table = self.query_one(DataTable)
        table.clear(columns=True)

        sort_indicators = {
            SortMode.NAME: ("↓", "", "", "", ""),
            SortMode.MODIFIED: ("", "", "", "", "↓"),
            SortMode.STATUS: ("", "", "↓", "", ""),
            SortMode.BRANCH: ("", "↓", "", "", ""),
        }
        indicators = sort_indicators.get(self._sort_mode, ("", "", "", "", ""))

        table.add_column(f"Name {indicators[0]}".strip(), width=30)
        table.add_column(f"Branch {indicators[1]}".strip(), width=25)
        table.add_column(f"Status {indicators[2]}".strip(), width=20)
        table.add_column("PR", width=45)
        table.add_column(f"Modified {indicators[4]}".strip(), width=15)
        table.cursor_type = "row"
        table.zebra_stripes = True

        for repo_path in sorted_paths:
            summary = filtered[repo_path]
            status_icon = "⚠ " if summary.status != RepoStatus.OK else ""
            pr_text = (
                f"#{summary.pr_info.number}: {summary.pr_info.title}"
                if summary.pr_info
                else "—"
            )

            table.add_row(
                truncate(summary.name, 28),
                truncate(summary.current_branch, 23),
                f"{status_icon}{summary.status_summary}",
                truncate(pr_text, 43),
                format_relative_time(summary.last_modified),
                key=str(repo_path),
            )

    def _update_repo_table_row(self, path: Path, summary: RepoSummary) -> None:
        """Update single row in repo list table"""
        self._refresh_table_with_filters()
        self._update_status_badges()

    def _update_filter_sort_status(self) -> None:
        """Update prominent filter/sort status indicator"""
        status_widget = self.query_one("#filter-sort-status", Static)

        parts = []
        if self._filter_mode != FilterMode.ALL:
            parts.append(f"[bold yellow]FILTER:[/bold yellow] {self._filter_mode.value}")

        if self._sort_mode != SortMode.NAME:
            parts.append(f"[bold cyan]SORT:[/bold cyan] {self._sort_mode.value}")

        if parts:
            status_widget.update("  ".join(parts))
            status_widget.styles.display = "block"
        else:
            status_widget.update("")
            status_widget.styles.display = "none"

    def _update_status_badges(self) -> None:
        """Update status badges in breadcrumb bar"""
        from multi_repo_view.filters import filter_repos

        if self._current_view != "repo_list":
            return

        total = len(self._repo_paths)
        filtered = filter_repos(self._summaries, self._filter_mode, self._filter_text)
        visible = len(filtered)

        dirty = sum(1 for s in filtered.values() if s.uncommitted_count > 0)
        with_pr = sum(1 for s in filtered.values() if s.pr_info)

        badges = [
            StatusBadge("repos", f"{visible}/{total}", "white", "grey37"),
            StatusBadge("dirty", str(dirty), "white", "darkorange3"),
            StatusBadge("PRs", str(with_pr), "white", "green4"),
        ]

        if self._filter_mode != FilterMode.ALL:
            badges.append(
                StatusBadge("filter", self._filter_mode.value, "black", "yellow3")
            )

        if self._sort_mode != SortMode.NAME:
            badges.append(
                StatusBadge("sort", self._sort_mode.value, "black", "cyan3")
            )

        breadcrumbs = self.query_one(Breadcrumbs)
        breadcrumbs.update_badges(badges)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        row_key = str(event.row_key.value)

        if self._current_view == "repo_list":
            repo_path = Path(row_key)
            if repo_path in self._summaries:
                self._selected_repo = repo_path
                self._show_repo_detail_view(repo_path)

        elif self._current_view == "repo_detail":
            if row_key.startswith("branch:"):
                branch_name = row_key.split(":", 1)[1]
                self._show_branch_detail_modal(branch_name)
            elif row_key.startswith("stash:"):
                stash_name = row_key.split(":", 1)[1]
                self._show_stash_detail_modal(stash_name)
            elif row_key.startswith("worktree:"):
                worktree_path = row_key.split(":", 1)[1]
                self._show_worktree_detail_modal(worktree_path)

    def _show_repo_detail_view(self, repo_path: Path) -> None:
        """Show repo detail view"""
        summary = self._summaries.get(repo_path)
        if not summary:
            return

        self._current_view = "repo_detail"
        self._breadcrumb_path = [summary.name]

        breadcrumbs = self.query_one(Breadcrumbs)
        breadcrumbs.update_path(self._breadcrumb_path)
        breadcrumbs.update_badges([])

        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_column("Kind", width=12)
        table.add_column("Name", width=40)
        table.add_column("Status", width=20)
        table.add_column("Reference", width=50)

        self.notify("Loading repo details...")
        self.run_worker(self._load_repo_details(repo_path), exclusive=True)

    async def _load_repo_details(self, repo_path: Path) -> None:
        """Load all branches, stashes, and worktrees for repo"""
        table = self.query_one(DataTable)

        branches, stashes, worktrees = await asyncio.gather(
            get_branch_list_async(repo_path),
            get_stash_list(repo_path),
            get_worktree_list(repo_path),
        )

        for branch in branches:
            ahead_behind = []
            if branch.ahead > 0:
                ahead_behind.append(f"↑{branch.ahead}")
            if branch.behind > 0:
                ahead_behind.append(f"↓{branch.behind}")
            status = " ".join(ahead_behind) if ahead_behind else "—"

            marker = "✓" if branch.is_current else ""
            name = f"{marker} {branch.name}".strip()

            table.add_row(
                "branch",
                truncate(name, 38),
                status,
                "...",
                key=f"branch:{branch.name}",
            )

        for stash in stashes:
            table.add_row(
                "stash",
                truncate(stash["name"], 38),
                "—",
                truncate(stash["message"], 48),
                key=f"stash:{stash['name']}",
            )

        for worktree in worktrees:
            status = "detached" if worktree.is_detached else "—"
            table.add_row(
                "worktree",
                truncate(worktree.branch or "HEAD", 38),
                status,
                truncate(str(worktree.path.name), 48),
                key=f"worktree:{worktree.path}",
            )

        for branch in branches:
            self.run_worker(
                self._load_branch_pr(repo_path, branch),
                group="branch_prs",
                exclusive=False,
            )

    async def _load_branch_pr(self, repo_path: Path, branch: BranchInfo) -> None:
        """Load PR info for a branch"""
        upstream = await get_upstream_repo(repo_path)
        if not upstream:
            return

        cache_key = f"{upstream}:{branch.name}"
        pr_info = pr_cache.get(cache_key)

        if not pr_info:
            pr_info = await get_pr_for_branch_async(repo_path, branch.name)
            if pr_info:
                pr_cache.set(cache_key, pr_info)

        if pr_info:
            self._update_branch_pr_row(branch.name, pr_info)

    def _update_branch_pr_row(self, branch_name: str, pr_info) -> None:
        """Update PR info for a branch row"""
        table = self.query_one(DataTable)
        row_key = f"branch:{branch_name}"
        try:
            pr_text = f"#{pr_info.number}: {truncate(pr_info.title, 42)}"
            table.update_cell(row_key, "Reference", pr_text)
        except Exception:
            pass

    def _show_branch_detail_modal(self, branch_name: str) -> None:
        """Show branch detail modal"""
        if not self._selected_repo:
            return

        pr_detail = None

        async def get_pr():
            nonlocal pr_detail
            from multi_repo_view.github_ops import get_pr_detail

            pr_detail = await get_pr_detail(self._selected_repo, branch_name)

        self.run_worker(get_pr(), exclusive=False)

        self.push_screen(
            BranchDetailModal(self._selected_repo, branch_name, pr_detail)
        )

    def _show_stash_detail_modal(self, stash_name: str) -> None:
        """Show stash detail modal"""
        if not self._selected_repo:
            return
        self.push_screen(StashDetailModal(self._selected_repo, stash_name))

    def _show_worktree_detail_modal(self, worktree_path: str) -> None:
        """Show worktree detail modal"""
        if not self._selected_repo:
            return
        self.push_screen(WorktreeDetailModal(self._selected_repo, worktree_path))

    def action_cursor_down(self) -> None:
        """Move cursor down"""
        table = self.query_one(DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up"""
        table = self.query_one(DataTable)
        table.action_cursor_up()

    def action_jump_top(self) -> None:
        """Jump to top"""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.move_cursor(row=0)

    def action_jump_bottom(self) -> None:
        """Jump to bottom"""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.move_cursor(row=table.row_count - 1)

    def action_select(self) -> None:
        """Select current row"""
        table = self.query_one(DataTable)
        if table.cursor_row is None:
            return

        row_keys = list(table.rows.keys())
        if table.cursor_row >= len(row_keys):
            return

        row_key = str(row_keys[table.cursor_row])

        if self._current_view == "repo_list":
            repo_path = Path(row_key)
            if repo_path in self._summaries:
                self._selected_repo = repo_path
                self._show_repo_detail_view(repo_path)

        elif self._current_view == "repo_detail":
            if row_key.startswith("branch:"):
                branch_name = row_key.split(":", 1)[1]
                self._show_branch_detail_modal(branch_name)
            elif row_key.startswith("stash:"):
                stash_name = row_key.split(":", 1)[1]
                self._show_stash_detail_modal(stash_name)
            elif row_key.startswith("worktree:"):
                worktree_path = row_key.split(":", 1)[1]
                self._show_worktree_detail_modal(worktree_path)

    def action_back(self) -> None:
        """Go back to previous view"""
        if self._current_view == "repo_detail":
            self._current_view = "repo_list"
            self._selected_repo = None
            self._breadcrumb_path = []
            self._show_repo_list_table()
            self._update_status_badges()
            self._update_filter_sort_status()
            self._start_progressive_load()

    def action_refresh(self) -> None:
        """Refresh all data"""
        pr_cache.clear()
        branch_cache.clear()
        commit_cache.clear()
        self._summaries.clear()
        self._filter_mode = FilterMode.ALL
        self._sort_mode = SortMode.NAME

        if self._current_view == "repo_list":
            self._show_repo_list_table()
            self._start_progressive_load()
        else:
            self.action_back()

        self.notify("Refreshing...")

    def action_open_pr(self) -> None:
        """Open PR in browser"""
        if self._current_view == "repo_list" and self._repo_paths:
            table = self.query_one(DataTable)
            if table.cursor_row is not None:
                try:
                    row_key = list(table.rows.keys())[table.cursor_row]
                    repo_path = Path(str(row_key))
                    summary = self._summaries.get(repo_path)
                    if summary and summary.pr_info:
                        webbrowser.open(summary.pr_info.url)
                        self.notify(f"Opening {summary.pr_info.url}")
                    else:
                        self.notify("No PR for current branch", severity="warning")
                except Exception:
                    pass

    def action_copy(self) -> None:
        """Show copy popup with context-aware options"""
        table = self.query_one(DataTable)

        branch_name = None
        pr_number = None
        pr_url = None
        repo_path = None

        if self._current_view == "repo_list":
            if table.cursor_row is not None:
                row_keys = list(table.rows.keys())
                if table.cursor_row < len(row_keys):
                    row_key = str(row_keys[table.cursor_row])
                    repo_path = Path(row_key)
                    summary = self._summaries.get(repo_path)
                    if summary:
                        branch_name = summary.current_branch
                        if summary.pr_info:
                            pr_number = summary.pr_info.number
                            pr_url = summary.pr_info.url

        elif self._current_view == "repo_detail":
            repo_path = self._selected_repo
            if table.cursor_row is not None:
                row_keys = list(table.rows.keys())
                if table.cursor_row < len(row_keys):
                    row_key = str(row_keys[table.cursor_row])
                    if row_key.startswith("branch:"):
                        branch_name = row_key.split(":", 1)[1]

        self.push_screen(
            CopyPopup(
                branch_name=branch_name,
                pr_number=pr_number,
                pr_url=pr_url,
                repo_path=repo_path,
            )
        )

    def action_cycle_filter(self) -> None:
        modes = list(FilterMode)
        current_idx = modes.index(self._filter_mode)
        self._filter_mode = modes[(current_idx + 1) % len(modes)]
        self._refresh_table_with_filters()
        self._update_status_badges()
        self._update_filter_sort_status()

    def action_cycle_sort(self) -> None:
        modes = list(SortMode)
        current_idx = modes.index(self._sort_mode)
        self._sort_mode = modes[(current_idx + 1) % len(modes)]
        self._refresh_table_with_filters()
        self._update_status_badges()
        self._update_filter_sort_status()

    def action_help(self) -> None:
        """Show help modal"""
        self.push_screen(HelpModal(self.theme_name))
