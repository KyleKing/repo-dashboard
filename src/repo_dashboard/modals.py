from pathlib import Path

import pyperclip
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, LoadingIndicator, ProgressBar, Static

from repo_dashboard.models import ActiveFilter, CommitInfo, FilterMode, PRDetail, SortMode, WorkflowSummary


def _format_commits(commits: list[CommitInfo], max_display: int = 10) -> str:
    """Format commit list with truncation"""
    if not commits:
        return "[#a5adcb]No commits[/]"

    lines = []
    for commit in commits[:max_display]:
        lines.append(f"[#8bd5ca]{commit.sha}[/] [#a5adcb]{commit.relative_time}[/]")
        lines.append(f"  {commit.message}")
        lines.append(f"  [#a5adcb]{commit.author}[/]")
        lines.append("")

    if len(commits) > max_display:
        lines.append(f"[#a5adcb]... and {len(commits) - max_display} more[/]")

    return "\n".join(lines)


def _format_files(files: list[str], prefix: str = "") -> str:
    """Format file list"""
    if not files:
        return "[#a5adcb]No files[/]"
    return "\n".join(f"{prefix}{f}" for f in files)


def _format_pr_detail(pr: PRDetail) -> str:
    """Format PR with checks and stats"""
    status_map = {
        "passing": ("✓", "#a6da95"),
        "failing": ("✗", "#ed8796"),
        "pending": ("○", "#eed49f"),
    }
    icon, color = status_map.get(pr.checks_status or "unknown", ("?", "#a5adcb"))

    lines = [
        f"[bold]PR #{pr.number}:[/] {pr.title}",
        f"State: {pr.state}  Checks: [{color}]{icon}[/] {pr.checks_status or 'unknown'}",
        f"[#a6da95]+{pr.additions}[/] [#ed8796]-{pr.deletions}[/]  Comments: {pr.unresolved_comments}",
        "",
        pr.description[:300] + "..." if len(pr.description) > 300 else pr.description,
    ]
    return "\n".join(lines)


def _format_workflow_runs(workflow_summary: WorkflowSummary) -> str:
    """Format workflow runs with status icons"""
    if not workflow_summary or not workflow_summary.runs:
        return "[#a5adcb]No workflow runs[/]"

    lines = []
    status_map = {
        "success": ("✓", "#a6da95"),
        "failure": ("✗", "#ed8796"),
        "timed_out": ("✗", "#ed8796"),
        "action_required": ("!", "#eed49f"),
        "skipped": ("○", "#a5adcb"),
        "cancelled": ("⊘", "#a5adcb"),
        "neutral": ("—", "#a5adcb"),
    }

    for run in workflow_summary.runs:
        if run.status == "completed" and run.conclusion:
            icon, color = status_map.get(run.conclusion, ("?", "#a5adcb"))
            status_text = f"[{color}]{icon}[/] {run.conclusion}"
        else:
            status_text = f"[#eed49f]◷[/] {run.status}"

        lines.append(f"{run.workflow_name}: {status_text}")

    return "\n".join(lines)


class BaseDetailModal(ModalScreen):
    """Base class for detail modals with loading state and scrolling"""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
    ]

    def __init__(self, title: str):
        super().__init__()
        self.modal_title = title

    def compose(self) -> ComposeResult:
        with Vertical(classes="detail-modal-container"):
            yield Static(self.modal_title, classes="detail-modal-title")
            with ScrollableContainer(classes="detail-modal-content"):
                yield LoadingIndicator()
            yield Static("[#a5adcb]Esc[/] to close", classes="detail-modal-footer")

    async def on_mount(self) -> None:
        try:
            content = await self.load_content()
            container = self.query_one(ScrollableContainer)
            container.query_one(LoadingIndicator).remove()
            container.mount(Static(content, markup=True))
        except Exception as e:
            container = self.query_one(ScrollableContainer)
            container.query_one(LoadingIndicator).remove()
            container.mount(Static(f"[#ed8796]Error:[/] {str(e)}", markup=True))

    async def load_content(self) -> str:
        """Override in subclasses"""
        raise NotImplementedError

    def action_scroll_down(self) -> None:
        self.query_one(ScrollableContainer).scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one(ScrollableContainer).scroll_up()


class BranchDetailModal(BaseDetailModal):
    """Modal for displaying branch details"""

    def __init__(self, repo_path: Path, branch_name: str, pr_detail: PRDetail | None):
        super().__init__(f"Branch: {branch_name}")
        self.repo_path = repo_path
        self.branch_name = branch_name
        self.pr_detail = pr_detail

    async def load_content(self) -> str:
        from repo_dashboard.git_ops import get_branch_detail_async
        from repo_dashboard.github_ops import get_workflow_runs_for_commit
        from repo_dashboard.vcs_factory import get_vcs_operations

        detail = await get_branch_detail_async(
            self.repo_path,
            self.branch_name,
            self.pr_detail,
        )

        sections = []

        # Branch info section
        sections.append(f"[bold]Tracking:[/] {detail.branch_info.tracking or '[#a5adcb]No remote[/]'}")
        sections.append("")

        # PR section
        if detail.pr_detail:
            sections.append("[bold]Pull Request[/]")
            sections.append(_format_pr_detail(detail.pr_detail))
            sections.append("")

        # Workflow section
        vcs_ops = get_vcs_operations(self.repo_path)
        commit_sha = await vcs_ops.get_commit_sha(self.repo_path, self.branch_name)
        if commit_sha:
            workflow_summary = await get_workflow_runs_for_commit(self.repo_path, commit_sha)
            if workflow_summary:
                sections.append("[bold]Workflows[/]")
                sections.append(_format_workflow_runs(workflow_summary))
                sections.append("")

        # Status section
        status_parts = []
        if detail.branch_info.ahead > 0:
            status_parts.append(f"↑{detail.branch_info.ahead} ahead")
        if detail.branch_info.behind > 0:
            status_parts.append(f"↓{detail.branch_info.behind} behind")
        sections.append(f"[bold]Status:[/] {' '.join(status_parts) or 'Up to date'}")
        sections.append("")

        # Commits ahead
        if detail.commits_ahead:
            sections.append(f"[bold]Commits Ahead ({len(detail.commits_ahead)}):[/]")
            sections.append(_format_commits(detail.commits_ahead))
            sections.append("")

        # Commits behind
        if detail.commits_behind:
            sections.append(
                f"[bold]Commits Behind ({len(detail.commits_behind)}):[/]"
            )
            sections.append(_format_commits(detail.commits_behind))
            sections.append("")

        # Files
        if detail.modified_files or detail.staged_files or detail.untracked_files:
            sections.append("[bold]Working Directory:[/]")
            if detail.staged_files:
                sections.append(f"[#a6da95]Staged ({len(detail.staged_files)}):[/]")
                sections.append(_format_files(detail.staged_files, "  "))
            if detail.modified_files:
                sections.append(f"[#eed49f]Modified ({len(detail.modified_files)}):[/]")
                sections.append(_format_files(detail.modified_files, "  "))
            if detail.untracked_files:
                sections.append(f"[#ed8796]Untracked ({len(detail.untracked_files)}):[/]")
                sections.append(_format_files(detail.untracked_files, "  "))

        return "\n".join(sections)


class StashDetailModal(BaseDetailModal):
    """Modal for displaying stash details"""

    def __init__(self, repo_path: Path, stash_name: str):
        super().__init__(f"Stash: {stash_name}")
        self.repo_path = repo_path
        self.stash_name = stash_name

    async def load_content(self) -> str:
        from repo_dashboard.git_ops import get_stash_detail
        from repo_dashboard.utils import format_relative_time

        detail = await get_stash_detail(self.repo_path, self.stash_name)

        relative_time = format_relative_time(detail.date)
        full_date = detail.date.strftime("%Y-%m-%d %H:%M:%S")

        sections = [
            f"[bold]Message:[/] {detail.message}",
            f"[bold]Branch:[/] {detail.branch}",
            f"[bold]Created:[/] {relative_time} ({full_date})",
            "",
            f"[bold]Summary:[/]",
            f"  {len(detail.modified_files)} file(s) modified",
            "",
            f"[bold]Modified Files:[/]",
            _format_files(detail.modified_files),
        ]

        return "\n".join(sections)


class WorktreeDetailModal(BaseDetailModal):
    """Modal for displaying worktree details"""

    def __init__(self, repo_path: Path, worktree_path: str):
        super().__init__(f"Worktree: {Path(worktree_path).name}")
        self.repo_path = repo_path
        self.worktree_path = Path(worktree_path)

    async def load_content(self) -> str:
        from repo_dashboard.git_ops import (
            get_status_files_async,
            get_worktree_list,
        )

        worktrees = await get_worktree_list(self.repo_path)
        worktree = next(
            (w for w in worktrees if w.path == self.worktree_path), None
        )

        if not worktree:
            return "[#ed8796]Worktree not found[/]"

        sections = [
            f"[bold]Path:[/] {worktree.path}",
            f"[bold]Branch:[/] {worktree.branch or '[#ed8796]DETACHED[/]'}",
            f"[bold]Status:[/] {'🔒 Locked' if worktree.is_locked else '✓ Active'}",
            "",
        ]

        if worktree.is_detached:
            sections.append(
                "[#eed49f]Warning:[/] Worktree is in detached HEAD state"
            )
            sections.append("")

        try:
            untracked, modified, staged = await get_status_files_async(
                self.worktree_path
            )

            total_changes = len(untracked) + len(modified) + len(staged)
            if total_changes > 0:
                sections.append("[bold]Working Directory:[/]")
                if staged:
                    sections.append(f"[#a6da95]Staged ({len(staged)}):[/]")
                    sections.append(_format_files(staged, "  "))
                if modified:
                    sections.append(f"[#eed49f]Modified ({len(modified)}):[/]")
                    sections.append(_format_files(modified, "  "))
                if untracked:
                    sections.append(f"[#ed8796]Untracked ({len(untracked)}):[/]")
                    sections.append(_format_files(untracked, "  "))
            else:
                sections.append("[#a5adcb]No uncommitted changes[/]")
        except Exception:
            sections.append("[#a5adcb]Unable to fetch worktree status[/]")

        return "\n".join(sections)


class CopyPopup(ModalScreen):
    """Small popup for copying items to clipboard"""

    BINDINGS = [
        Binding("b", "copy_branch", "Branch", show=False),
        Binding("n", "copy_pr_number", "PR Number", show=False),
        Binding("u", "copy_pr_url", "PR URL", show=False),
        Binding("p", "copy_path", "Path", show=False),
        Binding("escape", "dismiss", "Cancel", show=False),
    ]

    def __init__(
        self,
        branch_name: str | None = None,
        pr_number: int | None = None,
        pr_url: str | None = None,
        repo_path: Path | None = None,
    ):
        super().__init__()
        self.branch_name = branch_name
        self.pr_number = pr_number
        self.pr_url = pr_url
        self.repo_path = repo_path

    def compose(self) -> ComposeResult:
        lines = ["[bold]Copy to clipboard:[/]", ""]

        if self.branch_name:
            lines.append("[b] Branch name")
        if self.pr_number:
            lines.append("[n] PR number")
        if self.pr_url:
            lines.append("[u] PR URL")
        if self.repo_path:
            lines.append("[p] Repo path")

        lines.append("")
        lines.append("[#a5adcb][Esc] Cancel[/]")

        with Vertical(classes="copy-popup-container"):
            yield Static("\n".join(lines), classes="copy-popup-content")

    def action_copy_branch(self) -> None:
        if self.branch_name:
            pyperclip.copy(self.branch_name)
            self.app.notify(f"Copied branch: {self.branch_name}")
            self.dismiss()

    def action_copy_pr_number(self) -> None:
        if self.pr_number:
            pyperclip.copy(str(self.pr_number))
            self.app.notify(f"Copied PR number: {self.pr_number}")
            self.dismiss()

    def action_copy_pr_url(self) -> None:
        if self.pr_url:
            pyperclip.copy(self.pr_url)
            self.app.notify("Copied PR URL")
            self.dismiss()

    def action_copy_path(self) -> None:
        if self.repo_path:
            pyperclip.copy(str(self.repo_path))
            self.app.notify(f"Copied path: {self.repo_path.name}")
            self.dismiss()


class FilterPopup(ModalScreen):
    """Popup for selecting filters with chord-based input"""

    BINDINGS = [
        Binding("a", "toggle_ahead", "Ahead", show=False),
        Binding("b", "toggle_behind", "Behind", show=False),
        Binding("c", "clear_all", "Clear", show=False),
        Binding("d", "toggle_dirty", "Dirty", show=False),
        Binding("escape", "dismiss", "Close", show=False),
        Binding("n", "start_not", "Not", show=False),
        Binding("p", "toggle_pr", "PR", show=False),
        Binding("s", "toggle_stash", "Stash", show=False),
    ]

    def __init__(self, active_filters: list[ActiveFilter]):
        super().__init__()
        self._active_filters = list(active_filters)
        self._not_mode = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="filter-popup-container"):
            yield Static("", id="filter-popup-content", classes="filter-popup-content")

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        lines = ["[bold]Filter[/] (AND logic)", ""]

        not_prefix = "[#c6a0f6]NOT [/]" if self._not_mode else "    "
        lines.append(f"{not_prefix}\\[a] Ahead")
        lines.append(f"{not_prefix}\\[b] Behind")
        lines.append(f"{not_prefix}\\[d] Dirty")
        lines.append(f"{not_prefix}\\[p] Has PR")
        lines.append(f"{not_prefix}\\[s] Has Stash")
        lines.append("")
        lines.append("\\[n] Not...")
        lines.append("\\[c] Clear")
        lines.append("\\[Esc] Close")

        if self._active_filters:
            active_str = ", ".join(f.display_name for f in self._active_filters)
            lines.append("")
            lines.append(f"[#8aadf4]Active: {active_str}[/]")

        content = self.query_one("#filter-popup-content", Static)
        content.update("\n".join(lines))

    def _toggle_filter(self, mode: FilterMode) -> None:
        new_filter = ActiveFilter(mode=mode, inverted=self._not_mode)
        existing = next(
            (i for i, f in enumerate(self._active_filters) if f.mode == mode),
            None,
        )
        if existing is not None:
            if self._active_filters[existing].inverted == self._not_mode:
                self._active_filters.pop(existing)
            else:
                self._active_filters[existing] = new_filter
        else:
            self._active_filters.append(new_filter)

        self._not_mode = False
        self._update_display()
        self.dismiss(self._active_filters)

    def action_start_not(self) -> None:
        self._not_mode = not self._not_mode
        self._update_display()

    def action_toggle_ahead(self) -> None:
        self._toggle_filter(FilterMode.AHEAD)

    def action_toggle_behind(self) -> None:
        self._toggle_filter(FilterMode.BEHIND)

    def action_toggle_dirty(self) -> None:
        self._toggle_filter(FilterMode.DIRTY)

    def action_toggle_pr(self) -> None:
        self._toggle_filter(FilterMode.HAS_PR)

    def action_toggle_stash(self) -> None:
        self._toggle_filter(FilterMode.HAS_STASH)

    def action_clear_all(self) -> None:
        self._active_filters = []
        self.dismiss(self._active_filters)


class SortPopup(ModalScreen):
    """Popup for selecting sort mode"""

    BINDINGS = [
        Binding("b", "sort_branch", "Branch", show=False),
        Binding("B", "sort_branch_rev", "Branch Rev", show=False),
        Binding("c", "clear", "Clear", show=False),
        Binding("escape", "dismiss", "Close", show=False),
        Binding("m", "sort_modified", "Modified", show=False),
        Binding("M", "sort_modified_rev", "Modified Rev", show=False),
        Binding("n", "sort_name", "Name", show=False),
        Binding("N", "sort_name_rev", "Name Rev", show=False),
        Binding("s", "sort_status", "Status", show=False),
        Binding("S", "sort_status_rev", "Status Rev", show=False),
    ]

    def __init__(self, current_mode: SortMode, current_reverse: bool):
        super().__init__()
        self._mode = current_mode
        self._reverse = current_reverse

    def compose(self) -> ComposeResult:
        lines = [
            "[bold]Sort[/] (UPPERCASE=reverse)",
            "",
            "\\[b/B] Branch",
            "\\[m/M] Modified",
            "\\[n/N] Name",
            "\\[s/S] Status",
            "",
            "\\[c] Clear",
            "\\[Esc] Close",
            "",
        ]

        direction = "desc" if self._reverse else "asc"
        lines.append(f"[#8aadf4]Active: {self._mode.value} ({direction})[/]")

        with Vertical(classes="sort-popup-container"):
            yield Static("\n".join(lines), classes="sort-popup-content")

    def _select_sort(self, mode: SortMode, reverse: bool) -> None:
        self.dismiss((mode, reverse))

    def action_clear(self) -> None:
        self._select_sort(SortMode.NAME, False)

    def action_sort_branch(self) -> None:
        self._select_sort(SortMode.BRANCH, False)

    def action_sort_branch_rev(self) -> None:
        self._select_sort(SortMode.BRANCH, True)

    def action_sort_modified(self) -> None:
        self._select_sort(SortMode.MODIFIED, False)

    def action_sort_modified_rev(self) -> None:
        self._select_sort(SortMode.MODIFIED, True)

    def action_sort_name(self) -> None:
        self._select_sort(SortMode.NAME, False)

    def action_sort_name_rev(self) -> None:
        self._select_sort(SortMode.NAME, True)

    def action_sort_status(self) -> None:
        self._select_sort(SortMode.STATUS, False)

    def action_sort_status_rev(self) -> None:
        self._select_sort(SortMode.STATUS, True)


def _detail_row(label: str, value: str) -> Horizontal:
    return Horizontal(
        Static(f"{label}:", classes="detail-label"),
        Static(value, classes="detail-value", markup=True),
        classes="detail-row",
    )


def _section_header(title: str) -> Static:
    return Static(f"[bold]{title}[/]", classes="detail-section-header", markup=True)


class DetailPanel(ScrollableContainer):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._repo_path: Path | None = None
        self._current_item: str | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[#a5adcb]Select an item to view details[/]",
            id="detail-panel-title",
            classes="detail-panel-title",
            markup=True,
        )
        yield Vertical(id="detail-panel-content")

    def clear(self) -> None:
        self._current_item = None
        title = self.query_one("#detail-panel-title", Static)
        title.update("[#a5adcb]Select an item to view details[/]")
        content = self.query_one("#detail-panel-content", Vertical)
        content.remove_children()

    def set_loading(self, title: str) -> None:
        title_widget = self.query_one("#detail-panel-title", Static)
        title_widget.update(f"[bold]{title}[/]")
        content = self.query_one("#detail-panel-content", Vertical)
        content.remove_children()
        content.mount(LoadingIndicator())

    def _set_loading(self, title: str) -> None:
        self.set_loading(title)

    def _set_content(self, title: str, widgets: list) -> None:
        title_widget = self.query_one("#detail-panel-title", Static)
        title_widget.update(f"[bold]{title}[/]")
        content = self.query_one("#detail-panel-content", Vertical)
        content.remove_children()
        for widget in widgets:
            content.mount(widget)

    def _set_error(self, title: str, message: str) -> None:
        title_widget = self.query_one("#detail-panel-title", Static)
        title_widget.update(f"[bold]{title}[/]")
        content = self.query_one("#detail-panel-content", Vertical)
        content.remove_children()
        content.mount(Static(f"[#ed8796]Error:[/] {message}", markup=True))

    async def show_branch(
        self, repo_path: Path, branch_name: str, pr_detail: PRDetail | None
    ) -> None:
        from repo_dashboard.git_ops import get_branch_detail_async

        self._repo_path = repo_path
        self._current_item = f"branch:{branch_name}"
        self._set_loading(f"Branch: {branch_name}")

        try:
            detail = await get_branch_detail_async(repo_path, branch_name, pr_detail)
            widgets = []

            widgets.append(
                _detail_row(
                    "Tracking", detail.branch_info.tracking or "[#a5adcb]No remote[/]"
                )
            )

            status_parts = []
            if detail.branch_info.ahead > 0:
                status_parts.append(f"[#a6da95]↑{detail.branch_info.ahead} ahead[/]")
            if detail.branch_info.behind > 0:
                status_parts.append(f"[#eed49f]↓{detail.branch_info.behind} behind[/]")
            widgets.append(
                _detail_row("Status", " ".join(status_parts) or "[#a5adcb]Up to date[/]")
            )

            if detail.pr_detail:
                pr = detail.pr_detail
                widgets.append(_section_header("Pull Request"))
                widgets.append(_detail_row("PR", f"#{pr.number}: {pr.title}"))
                status_map = {
                    "passing": ("[#a6da95]✓ passing[/]"),
                    "failing": ("[#ed8796]✗ failing[/]"),
                    "pending": ("[#eed49f]○ pending[/]"),
                }
                checks = status_map.get(pr.checks_status or "", f"[#a5adcb]{pr.checks_status or 'unknown'}[/]")
                widgets.append(_detail_row("State", f"{pr.state}  Checks: {checks}"))
                widgets.append(
                    _detail_row(
                        "Changes",
                        f"[#a6da95]+{pr.additions}[/] [#ed8796]-{pr.deletions}[/]  Comments: {pr.unresolved_comments}",
                    )
                )

            if detail.commits_ahead:
                widgets.append(
                    _section_header(f"Commits Ahead ({len(detail.commits_ahead)})")
                )
                widgets.append(
                    Static(_format_commits(detail.commits_ahead, 5), markup=True)
                )

            if detail.commits_behind:
                widgets.append(
                    _section_header(f"Commits Behind ({len(detail.commits_behind)})")
                )
                widgets.append(
                    Static(_format_commits(detail.commits_behind, 5), markup=True)
                )

            if detail.modified_files or detail.staged_files or detail.untracked_files:
                widgets.append(_section_header("Working Directory"))
                if detail.staged_files:
                    widgets.append(
                        _detail_row(
                            f"[#a6da95]Staged ({len(detail.staged_files)})[/]",
                            _format_files(detail.staged_files[:5]),
                        )
                    )
                if detail.modified_files:
                    widgets.append(
                        _detail_row(
                            f"[#eed49f]Modified ({len(detail.modified_files)})[/]",
                            _format_files(detail.modified_files[:5]),
                        )
                    )
                if detail.untracked_files:
                    widgets.append(
                        _detail_row(
                            f"[#ed8796]Untracked ({len(detail.untracked_files)})[/]",
                            _format_files(detail.untracked_files[:5]),
                        )
                    )

            self._set_content(f"Branch: {branch_name}", widgets)
        except Exception as err:
            self._set_error(f"Branch: {branch_name}", str(err))

    async def show_stash(self, repo_path: Path, stash_name: str) -> None:
        from repo_dashboard.git_ops import get_stash_detail
        from repo_dashboard.utils import format_relative_time

        self._repo_path = repo_path
        self._current_item = f"stash:{stash_name}"
        self._set_loading(f"Stash: {stash_name}")

        try:
            detail = await get_stash_detail(repo_path, stash_name)
            relative_time = format_relative_time(detail.date)
            full_date = detail.date.strftime("%Y-%m-%d %H:%M:%S")

            widgets = [
                _detail_row("Message", detail.message),
                _detail_row("Branch", detail.branch),
                _detail_row("Created", f"{relative_time} ({full_date})"),
                _detail_row("Summary", f"{len(detail.modified_files)} file(s) modified"),
            ]

            if detail.modified_files:
                widgets.append(_section_header("Modified Files"))
                widgets.append(Static(_format_files(detail.modified_files), markup=True))

            self._set_content(f"Stash: {stash_name}", widgets)
        except Exception as err:
            self._set_error(f"Stash: {stash_name}", str(err))

    async def show_worktree(self, repo_path: Path, worktree_path: str) -> None:
        from repo_dashboard.git_ops import get_status_files_async, get_worktree_list

        self._repo_path = repo_path
        self._current_item = f"worktree:{worktree_path}"
        worktree_path_obj = Path(worktree_path)
        self._set_loading(f"Worktree: {worktree_path_obj.name}")

        try:
            worktrees = await get_worktree_list(repo_path)
            worktree = next(
                (w for w in worktrees if w.path == worktree_path_obj), None
            )

            if not worktree:
                self._set_error(f"Worktree: {worktree_path_obj.name}", "Worktree not found")
                return

            status_icon = "🔒 Locked" if worktree.is_locked else "✓ Active"
            widgets = [
                _detail_row("Path", str(worktree.path)),
                _detail_row("Branch", worktree.branch or "[#ed8796]DETACHED[/]"),
                _detail_row("Status", status_icon),
            ]

            if worktree.is_detached:
                widgets.append(
                    Static(
                        "[#eed49f]Warning: Worktree is in detached HEAD state[/]",
                        markup=True,
                    )
                )

            try:
                untracked, modified, staged = await get_status_files_async(
                    worktree_path_obj
                )
                total_changes = len(untracked) + len(modified) + len(staged)
                if total_changes > 0:
                    widgets.append(_section_header("Working Directory"))
                    if staged:
                        widgets.append(
                            _detail_row(
                                f"[#a6da95]Staged ({len(staged)})[/]",
                                _format_files(staged[:5]),
                            )
                        )
                    if modified:
                        widgets.append(
                            _detail_row(
                                f"[#eed49f]Modified ({len(modified)})[/]",
                                _format_files(modified[:5]),
                            )
                        )
                    if untracked:
                        widgets.append(
                            _detail_row(
                                f"[#ed8796]Untracked ({len(untracked)})[/]",
                                _format_files(untracked[:5]),
                            )
                        )
                else:
                    widgets.append(Static("[#a5adcb]No uncommitted changes[/]", markup=True))
            except Exception:
                widgets.append(Static("[#a5adcb]Unable to fetch worktree status[/]", markup=True))

            self._set_content(f"Worktree: {worktree_path_obj.name}", widgets)
        except Exception as err:
            self._set_error(f"Worktree: {worktree_path_obj.name}", str(err))


class BatchTaskModal(ModalScreen):
    """Modal for running batch tasks with progress and results"""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, task_name: str, task_fn: callable, repos: list):
        super().__init__()
        self.task_name = task_name
        self.task_fn = task_fn
        self.repos = repos
        self._completed = 0
        self._total = len(repos)

    def compose(self) -> ComposeResult:
        with Vertical(classes="batch-task-modal-container"):
            yield Static(
                f"[bold]{self.task_name}[/]",
                classes="batch-task-title",
                markup=True,
            )
            yield Static(
                f"Running on {self._total} repositories",
                classes="batch-task-subtitle",
            )
            yield ProgressBar(total=self._total, id="batch-progress")
            with ScrollableContainer(classes="batch-task-results"):
                yield DataTable(id="batch-results-table", zebra_stripes=True)
            yield Static(
                "[#a5adcb]Esc[/] to close",
                classes="batch-task-footer",
                markup=True,
            )

    async def on_mount(self) -> None:
        from repo_dashboard.batch_tasks import BatchTaskRunner

        table = self.query_one("#batch-results-table", DataTable)
        table.add_column("Repository", width=30)
        table.add_column("Status", width=10)
        table.add_column("Message", width=60)
        table.add_column("Time", width=10)

        progress = self.query_one("#batch-progress", ProgressBar)

        runner = BatchTaskRunner(self.repos)

        for repo in self.repos:
            from repo_dashboard.vcs_factory import get_vcs_operations

            vcs_ops = get_vcs_operations(repo.path)
            import time

            start = time.time()

            try:
                success, message = await self.task_fn(vcs_ops, repo.path)
            except Exception as err:
                success, message = False, f"Error: {err}"

            duration = int((time.time() - start) * 1000)

            status_icon = "[#a6da95]✓[/]" if success else "[#ed8796]✗[/]"
            message_display = message[:57] + "..." if len(message) > 60 else message

            table.add_row(
                repo.name[:28],
                status_icon,
                message_display,
                f"{duration}ms",
            )

            self._completed += 1
            progress.update(progress=self._completed)


class HelpModal(ModalScreen):
    """Display help and keybindings"""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, theme_name: str):
        super().__init__()
        self.theme_name = theme_name

    def compose(self) -> ComposeResult:
        from textwrap import dedent

        help_text = dedent("""\
            [bold]Navigation[/]
            j/k or ↓/↑    Navigate up/down
            g/G           Jump to top/bottom
            Ctrl+D/U      Half-page down/up
            space/enter   Select item
            escape        Clear filters/search or go back
            /             Search (type query, Enter to confirm, Esc to cancel)

            [bold]Actions[/]
            c             Copy (branch/PR/path)
            o             Open PR in browser
            r             Refresh all data
            f             Filter popup (multiple, AND logic)
            s             Sort popup
            ?             Help (this screen)
            q             Quit

            [bold]Batch Tasks[/]
            F             Fetch all (filtered repos)
            P             Prune remote (filtered repos)
            C             Cleanup merged branches (filtered repos)

            [bold]Filter Popup (f)[/]
            d/a/b/p/s     Toggle dirty/ahead/behind/pr/stash
            n + key       Invert filter (e.g., n d = not dirty)
            c             Clear all filters

            [bold]Sort Popup (s)[/]
            n/m/s/b       Sort by name/modified/status/branch
            N/M/S/B       Reverse sort (uppercase)
            c             Clear (reset to name asc)

            [bold]Current Theme[/]
            {self.theme_name}""")

        with Vertical(classes="help-modal-container"):
            yield Static(help_text, classes="help-modal-content")
