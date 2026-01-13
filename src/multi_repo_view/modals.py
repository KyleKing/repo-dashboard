from pathlib import Path

import pyperclip
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import LoadingIndicator, Static

from multi_repo_view.models import CommitInfo, PRDetail


def _format_commits(commits: list[CommitInfo], max_display: int = 10) -> str:
    """Format commit list with truncation"""
    if not commits:
        return "[dim]No commits[/]"

    lines = []
    for commit in commits[:max_display]:
        lines.append(f"[cyan]{commit.sha}[/] [dim]{commit.relative_time}[/]")
        lines.append(f"  {commit.message}")
        lines.append(f"  [dim]{commit.author}[/]")
        lines.append("")

    if len(commits) > max_display:
        lines.append(f"[dim]... and {len(commits) - max_display} more[/]")

    return "\n".join(lines)


def _format_files(files: list[str], prefix: str = "") -> str:
    """Format file list"""
    if not files:
        return "[dim]No files[/]"
    return "\n".join(f"{prefix}{f}" for f in files)


def _format_pr_detail(pr: PRDetail) -> str:
    """Format PR with checks and stats"""
    status_map = {
        "passing": ("✓", "green"),
        "failing": ("✗", "red"),
        "pending": ("○", "yellow"),
    }
    icon, color = status_map.get(pr.checks_status or "unknown", ("?", "dim"))

    lines = [
        f"[bold]PR #{pr.number}:[/] {pr.title}",
        f"State: {pr.state}  Checks: [{color}]{icon}[/] {pr.checks_status or 'unknown'}",
        f"[green]+{pr.additions}[/] [red]-{pr.deletions}[/]  Comments: {pr.unresolved_comments}",
        "",
        pr.description[:300] + "..." if len(pr.description) > 300 else pr.description,
    ]
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
            yield Static("[dim]Esc[/] to close", classes="detail-modal-footer")

    async def on_mount(self) -> None:
        try:
            content = await self.load_content()
            container = self.query_one(ScrollableContainer)
            container.query_one(LoadingIndicator).remove()
            container.mount(Static(content, markup=True))
        except Exception as e:
            container = self.query_one(ScrollableContainer)
            container.query_one(LoadingIndicator).remove()
            container.mount(Static(f"[red]Error:[/] {str(e)}", markup=True))

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
        from multi_repo_view.git_ops import get_branch_detail_async

        detail = await get_branch_detail_async(
            self.repo_path,
            self.branch_name,
            self.pr_detail,
        )

        sections = []

        # Branch info section
        sections.append(f"[bold]Tracking:[/] {detail.branch_info.tracking or '[dim]No remote[/]'}")
        sections.append("")

        # PR section
        if detail.pr_detail:
            sections.append("[bold]Pull Request[/]")
            sections.append(_format_pr_detail(detail.pr_detail))
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
                sections.append(f"[green]Staged ({len(detail.staged_files)}):[/]")
                sections.append(_format_files(detail.staged_files, "  "))
            if detail.modified_files:
                sections.append(f"[yellow]Modified ({len(detail.modified_files)}):[/]")
                sections.append(_format_files(detail.modified_files, "  "))
            if detail.untracked_files:
                sections.append(f"[red]Untracked ({len(detail.untracked_files)}):[/]")
                sections.append(_format_files(detail.untracked_files, "  "))

        return "\n".join(sections)


class StashDetailModal(BaseDetailModal):
    """Modal for displaying stash details"""

    def __init__(self, repo_path: Path, stash_name: str):
        super().__init__(f"Stash: {stash_name}")
        self.repo_path = repo_path
        self.stash_name = stash_name

    async def load_content(self) -> str:
        from multi_repo_view.git_ops import get_stash_detail
        from multi_repo_view.utils import format_relative_time

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
        from multi_repo_view.git_ops import (
            get_status_files_async,
            get_worktree_list,
        )

        worktrees = await get_worktree_list(self.repo_path)
        worktree = next(
            (w for w in worktrees if w.path == self.worktree_path), None
        )

        if not worktree:
            return "[red]Worktree not found[/]"

        sections = [
            f"[bold]Path:[/] {worktree.path}",
            f"[bold]Branch:[/] {worktree.branch or '[red]DETACHED[/]'}",
            f"[bold]Status:[/] {'🔒 Locked' if worktree.is_locked else '✓ Active'}",
            "",
        ]

        if worktree.is_detached:
            sections.append(
                "[yellow]Warning:[/] Worktree is in detached HEAD state"
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
                    sections.append(f"[green]Staged ({len(staged)}):[/]")
                    sections.append(_format_files(staged, "  "))
                if modified:
                    sections.append(f"[yellow]Modified ({len(modified)}):[/]")
                    sections.append(_format_files(modified, "  "))
                if untracked:
                    sections.append(f"[red]Untracked ({len(untracked)}):[/]")
                    sections.append(_format_files(untracked, "  "))
            else:
                sections.append("[dim]No uncommitted changes[/]")
        except Exception:
            sections.append("[dim]Unable to fetch worktree status[/]")

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
        lines.append("[dim][Esc] Cancel[/]")

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
            space/enter   Select item
            escape        Go back

            [bold]Actions[/]
            c             Copy (branch/PR/path)
            o             Open PR in browser
            r             Refresh all data
            f             Cycle filter mode
            s             Cycle sort mode
            ?             Help (this screen)
            q             Quit

            [bold]Filter Modes[/]
            all → dirty → ahead → behind → has_pr → has_stash

            [bold]Sort Modes[/]
            name → modified → status → branch

            [bold]Current Theme[/]
            {self.theme_name}""")

        with Vertical(classes="help-modal-container"):
            yield Static(help_text, classes="help-modal-content")
