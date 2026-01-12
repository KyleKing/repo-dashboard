import asyncio
import webbrowser
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import DataTable, Footer, Static

from multi_repo_view.cache import pr_cache
from multi_repo_view.discovery import discover_git_repos
from multi_repo_view.git_ops import (
    get_branch_list_async,
    get_repo_summary_async,
    get_stash_list,
    get_upstream_repo,
    get_worktree_list,
)
from multi_repo_view.github_ops import get_pr_for_branch_async
from multi_repo_view.models import BranchInfo, RepoStatus, RepoSummary
from multi_repo_view.themes import CatppuccinLatte, CatppuccinMocha
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

    def compose(self) -> ComposeResult:
        yield Breadcrumbs([])
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

    def _update_repo_table_row(self, path: Path, summary: RepoSummary) -> None:
        """Update single row in repo list table"""
        table = self.query_one(DataTable)
        row_key = str(path)

        status_icon = "⚠ " if summary.status != RepoStatus.OK else ""
        pr_text = (
            f"#{summary.pr_info.number}: {summary.pr_info.title}"
            if summary.pr_info
            else "—"
        )

        try:
            table.update_cell(row_key, "Name", truncate(summary.name, 28))
            table.update_cell(
                row_key, "Branch", truncate(summary.current_branch, 23)
            )
            table.update_cell(
                row_key, "Status", f"{status_icon}{summary.status_summary}"
            )
            table.update_cell(row_key, "PR", truncate(pr_text, 43))
            table.update_cell(
                row_key, "Modified", format_relative_time(summary.last_modified)
            )
        except Exception:
            pass

        self._update_status_badges()

    def _update_status_badges(self) -> None:
        """Update status badges in breadcrumb bar"""
        if self._current_view != "repo_list":
            return

        total = len(self._repo_paths)
        loaded = len(self._summaries)
        dirty = sum(
            1 for s in self._summaries.values() if s.uncommitted_count > 0
        )
        with_pr = sum(1 for s in self._summaries.values() if s.pr_info)

        badges = [
            StatusBadge("repos", f"{loaded}/{total}", "white", "grey37"),
            StatusBadge("dirty", str(dirty), "white", "darkorange3"),
            StatusBadge("PRs", str(with_pr), "white", "green4"),
        ]

        breadcrumbs = self.query_one(Breadcrumbs)
        breadcrumbs.update_badges(badges)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        if self._current_view == "repo_list":
            row_key = event.row_key.value
            repo_path = Path(row_key)
            if repo_path in self._summaries:
                self._selected_repo = repo_path
                self._show_repo_detail_view(repo_path)

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
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)[0]
            if self._current_view == "repo_list":
                self.on_row_selected(
                    DataTable.RowSelected(table, row_key, table.cursor_row)
                )

    def action_back(self) -> None:
        """Go back to previous view"""
        if self._current_view == "repo_detail":
            self._current_view = "repo_list"
            self._selected_repo = None
            self._breadcrumb_path = []
            self._show_repo_list_table()
            self._update_status_badges()
            self._start_progressive_load()

    def action_refresh(self) -> None:
        """Refresh all data"""
        pr_cache.clear()
        self._summaries.clear()

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
        """Show copy popup"""
        self.notify("Copy functionality coming soon")

    def action_help(self) -> None:
        """Show help"""
        help_text = """
j/k or ↓/↑: Navigate
g/G: Jump to top/bottom
Space/Enter: Select
Esc: Back
o: Open PR
c: Copy
r: Refresh
q: Quit
?: Help
        """.strip()
        self.notify(help_text)
