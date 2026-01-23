import asyncio
import webbrowser
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Key
from textual.widgets import DataTable, Footer, Static

from repo_dashboard.cache import branch_cache, commit_cache, pr_cache
from repo_dashboard.discovery import discover_git_repos
from repo_dashboard.github_ops import get_pr_for_branch_async
from repo_dashboard.vcs_factory import get_vcs_operations
from repo_dashboard.modals import (
    CopyPopup,
    DetailPanel,
    FilterPopup,
    HelpModal,
    SortPopup,
)
from repo_dashboard.models import (
    ActiveFilter,
    BranchInfo,
    FilterMode,
    RepoStatus,
    RepoSummary,
    SortMode,
)
from repo_dashboard.utils import format_relative_time, truncate


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
            breadcrumb_text = f"[bold #24273a on #8aadf4] {crumbs[0]} [/]"
        else:
            parts = []
            for i, crumb in enumerate(crumbs):
                if i == len(crumbs) - 1:
                    parts.append(f"[bold #24273a on #8aadf4] {crumb} [/]")
                else:
                    parts.append(f"[#cad3f5 on #363a4f] {crumb} [/]")
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


class RepoDashboardApp(App):
    TITLE = "Repo Dashboard"

    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_pr", "Open PR"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "jump_top", "Top", show=False),
        Binding("G", "jump_bottom", "Bottom", show=False),
        Binding("ctrl+d", "page_down", "Page Down", show=False),
        Binding("ctrl+u", "page_up", "Page Up", show=False),
        Binding("space", "select", "Select", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("escape", "back", "Back", show=False),
        Binding("c", "copy", "Copy"),
        Binding("f", "show_filter_popup", "Filter"),
        Binding("s", "show_sort_popup", "Sort"),
        Binding("/", "search", "Search", show=False),
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
        self._active_filters: list[ActiveFilter] = []
        self._sort_mode: SortMode = SortMode.NAME
        self._sort_reverse: bool = False
        self._search_mode: bool = False
        self._search_text: str = ""
        self._branch_items: list[BranchInfo] = []
        self._stash_items: list[dict] = []
        self._worktree_items: list = []

    def compose(self) -> ComposeResult:
        yield Breadcrumbs([])
        yield Static("", id="filter-sort-status")
        with Vertical(id="main-layout"):
            with Container(id="main-container"):
                yield DataTable(id="main-table", zebra_stripes=False)
            yield DetailPanel(id="detail-panel")
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

        table = self.query_one(DataTable)
        table.focus()

    def _show_repo_list_table(self) -> None:
        """Show repo list table"""
        table = self.query_one(DataTable)
        table.clear(columns=True)

        table.add_column("Name", width=30)
        table.add_column("Branch", width=18)
        table.add_column("Status", width=20)
        table.add_column("PR", width=50)
        table.add_column("Modified", width=15)
        table.cursor_type = "row"

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
        vcs_ops = get_vcs_operations(path)
        summary = await vcs_ops.get_repo_summary_async(path)

        upstream = await vcs_ops.get_upstream_repo(path)
        if upstream:
            cache_key = f"{upstream}:{summary.current_branch}"
            if pr_info := pr_cache.get(cache_key):
                summary = RepoSummary(
                    path=summary.path,
                    name=summary.name,
                    vcs_type=summary.vcs_type,
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
                        vcs_type=summary.vcs_type,
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
        from repo_dashboard.filters import filter_repos_multi, sort_repos

        if self._current_view != "repo_list":
            return

        filtered = filter_repos_multi(self._summaries, self._active_filters, self._search_text)
        sorted_paths = sort_repos(list(filtered.keys()), filtered, self._sort_mode)
        if self._sort_reverse:
            sorted_paths = list(reversed(sorted_paths))

        table = self.query_one(DataTable)
        table.clear(columns=True)

        arrow = "↑" if self._sort_reverse else "↓"
        sort_indicators = {
            SortMode.NAME: (arrow, "", "", "", ""),
            SortMode.MODIFIED: ("", "", "", "", arrow),
            SortMode.STATUS: ("", "", arrow, "", ""),
            SortMode.BRANCH: ("", arrow, "", "", ""),
        }
        indicators = sort_indicators.get(self._sort_mode, ("", "", "", "", ""))

        table.add_column(f"Name {indicators[0]}".strip(), width=30)
        table.add_column(f"Branch {indicators[1]}".strip(), width=18)
        table.add_column(f"Status {indicators[2]}".strip(), width=20)
        table.add_column("PR", width=50)
        table.add_column(f"Modified {indicators[4]}".strip(), width=15)
        table.cursor_type = "row"

        for repo_path in sorted_paths:
            summary = filtered[repo_path]
            status_icon = "⚠ " if summary.status != RepoStatus.OK else ""
            pr_text = (
                f"#{summary.pr_info.number}: {summary.pr_info.title}"
                if summary.pr_info
                else "—"
            )

            if summary.ahead_count > 0 and summary.behind_count > 0:
                branch_color = "#ed8796"
            elif summary.ahead_count > 0:
                branch_color = "#eed49f"
            elif summary.behind_count > 0:
                branch_color = "#8aadf4"
            elif summary.uncommitted_count == 0:
                branch_color = "#a5adcb"
            else:
                branch_color = "#cad3f5"

            branch_text = truncate(summary.current_branch, 16)
            colored_branch = f"[{branch_color}]{branch_text}[/]"

            vcs_badge_color = "#c6a0f6" if summary.vcs_type == "jj" else "#8aadf4"
            vcs_badge = f"[{vcs_badge_color}]{summary.vcs_type}[/]"
            name_with_badge = f"{vcs_badge} {truncate(summary.name, 24)}"

            table.add_row(
                name_with_badge,
                colored_branch,
                f"{status_icon}{summary.status_summary}",
                truncate(pr_text, 48),
                format_relative_time(summary.last_modified),
                key=str(repo_path),
            )

    def _update_repo_table_row(self, path: Path, summary: RepoSummary) -> None:
        """Update single row in repo list table"""
        self._refresh_table_with_filters()
        self._update_status_badges()

    def _update_filter_sort_status(self) -> None:
        status_widget = self.query_one("#filter-sort-status", Static)

        parts = []
        if self._active_filters:
            filter_names = ", ".join(f.display_name for f in self._active_filters)
            parts.append(f"[bold yellow]FILTER:[/bold yellow] {filter_names}")

        if self._sort_mode != SortMode.NAME or self._sort_reverse:
            direction = " (rev)" if self._sort_reverse else ""
            parts.append(f"[bold cyan]SORT:[/bold cyan] {self._sort_mode.value}{direction}")

        if parts:
            status_widget.update("  ".join(parts))
            status_widget.styles.display = "block"
        else:
            status_widget.update("")
            status_widget.styles.display = "none"

    def _update_status_badges(self) -> None:
        from repo_dashboard.filters import filter_repos_multi

        if self._current_view != "repo_list":
            return

        total = len(self._repo_paths)
        filtered = filter_repos_multi(self._summaries, self._active_filters, self._search_text)
        visible = len(filtered)

        dirty = sum(1 for s in filtered.values() if s.uncommitted_count > 0)
        with_pr = sum(1 for s in filtered.values() if s.pr_info)

        git_count = sum(1 for s in filtered.values() if s.vcs_type == "git")
        jj_count = sum(1 for s in filtered.values() if s.vcs_type == "jj")

        badges = [
            StatusBadge("repos", f"{visible}/{total}", "#cad3f5", "#363a4f"),
        ]

        if git_count > 0:
            badges.append(StatusBadge("git", str(git_count), "#24273a", "#8aadf4"))
        if jj_count > 0:
            badges.append(StatusBadge("jj", str(jj_count), "#24273a", "#c6a0f6"))

        badges.extend([
            StatusBadge("dirty", str(dirty), "#24273a", "#f5a97f"),
            StatusBadge("PRs", str(with_pr), "#24273a", "#a6da95"),
        ])

        if self._active_filters:
            filter_keys = "".join(f.short_key for f in self._active_filters)
            badges.append(
                StatusBadge("filter", filter_keys, "#24273a", "#eed49f")
            )

        if self._sort_mode != SortMode.NAME or self._sort_reverse:
            sort_display = self._sort_mode.value[:3]
            if self._sort_reverse:
                sort_display += "!"
            badges.append(
                StatusBadge("sort", sort_display, "#24273a", "#8bd5ca")
            )

        if self._search_mode:
            search_display = f"/{self._search_text}_"
            badges.append(
                StatusBadge("search", search_display, "#24273a", "#c6a0f6")
            )
        elif self._search_text:
            badges.append(
                StatusBadge("search", f"/{self._search_text} ({visible})", "#24273a", "#c6a0f6")
            )

        breadcrumbs = self.query_one(Breadcrumbs)
        breadcrumbs.update_badges(badges)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter/Space)"""
        row_key = str(event.row_key.value)

        if self._current_view == "repo_list":
            repo_path = Path(row_key)
            if repo_path in self._summaries:
                self._selected_repo = repo_path
                self._show_repo_detail_view(repo_path)

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle cursor movement in repo detail view"""
        if self._current_view != "repo_detail":
            return

        row_key = str(event.row_key.value)
        if row_key.startswith("branch:"):
            branch_name = row_key.split(":", 1)[1]
            self._show_branch_detail(branch_name)
        elif row_key.startswith("stash:"):
            stash_name = row_key.split(":", 1)[1]
            self._show_stash_detail(stash_name)
        elif row_key.startswith("worktree:"):
            worktree_path = row_key.split(":", 1)[1]
            self._show_worktree_detail(worktree_path)

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

        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.display = True
        detail_panel.clear()

        self.notify("Loading repo details...")
        self.run_worker(self._load_repo_details(repo_path), exclusive=True)

    async def _load_repo_details(self, repo_path: Path) -> None:
        """Load all branches, stashes, and worktrees for repo"""
        vcs_ops = get_vcs_operations(repo_path)
        branches, stashes, worktrees = await asyncio.gather(
            vcs_ops.get_branch_list_async(repo_path),
            vcs_ops.get_stash_list(repo_path),
            vcs_ops.get_worktree_list(repo_path),
        )

        self._branch_items = branches
        self._stash_items = stashes
        self._worktree_items = worktrees

        self._refresh_repo_detail_table()

        for branch in self._branch_items:
            self.run_worker(
                self._load_branch_pr(repo_path, branch),
                group="branch_prs",
                exclusive=False,
            )

    def _refresh_repo_detail_table(self) -> None:
        """Refresh the repo detail table with current filters/sorts"""
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_column("Kind", width=12)
        table.add_column("Name", width=40)
        table.add_column("Status", width=20)
        table.add_column("Reference", width=50)

        filtered_branches = self._filter_branches(self._branch_items)
        sorted_branches = self._sort_branches(filtered_branches)

        first_row_key = None

        for branch in sorted_branches:
            ahead_behind = []
            if branch.ahead > 0:
                ahead_behind.append(f"↑{branch.ahead}")
            if branch.behind > 0:
                ahead_behind.append(f"↓{branch.behind}")
            status = " ".join(ahead_behind) if ahead_behind else "—"

            marker = "✓" if branch.is_current else ""
            name = f"{marker} {branch.name}".strip()

            row_key = f"branch:{branch.name}"
            table.add_row(
                "branch",
                truncate(name, 38),
                status,
                "...",
                key=row_key,
            )
            if first_row_key is None:
                first_row_key = row_key

        for stash in self._stash_items:
            row_key = f"stash:{stash['name']}"
            table.add_row(
                "stash",
                truncate(stash["name"], 38),
                "—",
                truncate(stash["message"], 48),
                key=row_key,
            )
            if first_row_key is None:
                first_row_key = row_key

        for worktree in self._worktree_items:
            status = "detached" if worktree.is_detached else "—"
            row_key = f"worktree:{worktree.path}"
            table.add_row(
                "worktree",
                truncate(worktree.branch or "HEAD", 38),
                status,
                truncate(str(worktree.path.name), 48),
                key=row_key,
            )
            if first_row_key is None:
                first_row_key = row_key

        if first_row_key and table.row_count > 0:
            table.move_cursor(row=0)
            if first_row_key.startswith("branch:"):
                branch_name = first_row_key.split(":", 1)[1]
                self._show_branch_detail(branch_name)
            elif first_row_key.startswith("stash:"):
                stash_name = first_row_key.split(":", 1)[1]
                self._show_stash_detail(stash_name)
            elif first_row_key.startswith("worktree:"):
                worktree_path = first_row_key.split(":", 1)[1]
                self._show_worktree_detail(worktree_path)
        else:
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            detail_panel.clear()

    def _filter_branches(self, branches: list[BranchInfo]) -> list[BranchInfo]:
        """Apply active filters to branch list"""
        if not self._active_filters:
            filtered = branches
        else:
            filtered = branches
            for active_filter in self._active_filters:
                filtered = self._apply_branch_filter(filtered, active_filter)

        if self._search_text:
            search_lower = self._search_text.lower()
            filtered = [b for b in filtered if search_lower in b.name.lower()]

        return filtered

    def _apply_branch_filter(
        self, branches: list[BranchInfo], active_filter: ActiveFilter
    ) -> list[BranchInfo]:
        """Apply a single filter to branches"""
        match active_filter.mode:
            case FilterMode.AHEAD:
                predicate = lambda b: b.ahead > 0
            case FilterMode.BEHIND:
                predicate = lambda b: b.behind > 0
            case FilterMode.DIRTY:
                predicate = lambda b: b.ahead > 0
            case _:
                predicate = lambda _: True

        if active_filter.inverted:
            return [b for b in branches if not predicate(b)]
        return [b for b in branches if predicate(b)]

    def _sort_branches(self, branches: list[BranchInfo]) -> list[BranchInfo]:
        """Sort branches based on current sort mode"""
        match self._sort_mode:
            case SortMode.NAME:
                sorted_branches = sorted(branches, key=lambda b: b.name.lower())
            case SortMode.STATUS:
                sorted_branches = sorted(
                    branches,
                    key=lambda b: (-b.ahead, -b.behind, b.name.lower()),
                )
            case SortMode.BRANCH:
                sorted_branches = sorted(branches, key=lambda b: b.name.lower())
            case _:
                sorted_branches = branches

        if self._sort_reverse:
            sorted_branches = list(reversed(sorted_branches))

        return sorted_branches

    async def _load_branch_pr(self, repo_path: Path, branch: BranchInfo) -> None:
        """Load PR info for a branch"""
        vcs_ops = get_vcs_operations(repo_path)
        upstream = await vcs_ops.get_upstream_repo(repo_path)
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

    def _show_branch_detail(self, branch_name: str) -> None:
        if not self._selected_repo:
            return

        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.set_loading(f"Branch: {branch_name}")

        async def load_branch() -> None:
            from repo_dashboard.github_ops import get_pr_detail

            pr_detail = await get_pr_detail(self._selected_repo, branch_name)
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            await detail_panel.show_branch(self._selected_repo, branch_name, pr_detail)

        self.run_worker(load_branch(), exclusive=True)

    def _show_stash_detail(self, stash_name: str) -> None:
        if not self._selected_repo:
            return

        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.set_loading(f"Stash: {stash_name}")

        async def load_stash() -> None:
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            await detail_panel.show_stash(self._selected_repo, stash_name)

        self.run_worker(load_stash(), exclusive=True)

    def _show_worktree_detail(self, worktree_path: str) -> None:
        if not self._selected_repo:
            return

        worktree_name = Path(worktree_path).name
        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.set_loading(f"Worktree: {worktree_name}")

        async def load_worktree() -> None:
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            await detail_panel.show_worktree(self._selected_repo, worktree_path)

        self.run_worker(load_worktree(), exclusive=True)

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
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.move_cursor(row=table.row_count - 1)

    def action_page_down(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        half_page = max(1, table.size.height // 2)
        current = table.cursor_row if table.cursor_row is not None else 0
        new_row = min(current + half_page, table.row_count - 1)
        table.move_cursor(row=new_row)

    def action_page_up(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        half_page = max(1, table.size.height // 2)
        current = table.cursor_row if table.cursor_row is not None else 0
        new_row = max(current - half_page, 0)
        table.move_cursor(row=new_row)

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

    def action_back(self) -> None:
        if self._search_mode:
            self._search_mode = False
            self._search_text = ""
            self._refresh_table_with_filters()
            self._update_status_badges()
            return

        if self._current_view == "repo_list":
            if self._active_filters or self._search_text:
                self._active_filters = []
                self._search_text = ""
                self._refresh_table_with_filters()
                self._update_status_badges()
                self._update_filter_sort_status()
                return

        if self._current_view == "repo_detail":
            self._current_view = "repo_list"
            self._selected_repo = None
            self._breadcrumb_path = []
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            detail_panel.display = False
            self._refresh_table_with_filters()
            self._update_status_badges()
            self._update_filter_sort_status()

    def action_refresh(self) -> None:
        pr_cache.clear()
        branch_cache.clear()
        commit_cache.clear()
        self._summaries.clear()
        self._active_filters = []
        self._sort_mode = SortMode.NAME
        self._sort_reverse = False
        self._search_text = ""
        self._search_mode = False

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

    def action_show_filter_popup(self) -> None:
        def handle_filter_result(result: list[ActiveFilter] | None) -> None:
            if result is not None:
                self._active_filters = result
                if self._current_view == "repo_list":
                    self._refresh_table_with_filters()
                    self._update_status_badges()
                    self._update_filter_sort_status()
                elif self._current_view == "repo_detail":
                    self._refresh_repo_detail_table()

        self.push_screen(FilterPopup(self._active_filters), handle_filter_result)

    def action_show_sort_popup(self) -> None:
        def handle_sort_result(result: tuple[SortMode, bool] | None) -> None:
            if result is not None:
                self._sort_mode, self._sort_reverse = result
                if self._current_view == "repo_list":
                    self._refresh_table_with_filters()
                    self._update_status_badges()
                    self._update_filter_sort_status()
                elif self._current_view == "repo_detail":
                    self._refresh_repo_detail_table()

        self.push_screen(SortPopup(self._sort_mode, self._sort_reverse), handle_sort_result)

    def action_help(self) -> None:
        """Show help modal"""
        self.push_screen(HelpModal(self.theme_name))

    def action_search(self) -> None:
        self._search_mode = True
        self._search_text = ""
        if self._current_view == "repo_list":
            self._update_status_badges()

    def on_key(self, event: Key) -> None:
        if not self._search_mode:
            return

        if event.key == "escape":
            self._search_mode = False
            self._search_text = ""
            if self._current_view == "repo_list":
                self._refresh_table_with_filters()
                self._update_status_badges()
            elif self._current_view == "repo_detail":
                self._refresh_repo_detail_table()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self._search_mode = False
            if self._current_view == "repo_list":
                self._update_status_badges()
            event.prevent_default()
            event.stop()
        elif event.key == "backspace":
            if self._search_text:
                self._search_text = self._search_text[:-1]
                if self._current_view == "repo_list":
                    self._refresh_table_with_filters()
                    self._update_status_badges()
                elif self._current_view == "repo_detail":
                    self._refresh_repo_detail_table()
            event.prevent_default()
            event.stop()
        elif event.is_printable and event.character:
            self._search_text += event.character
            if self._current_view == "repo_list":
                self._refresh_table_with_filters()
                self._update_status_badges()
            elif self._current_view == "repo_detail":
                self._refresh_repo_detail_table()
            event.prevent_default()
            event.stop()
