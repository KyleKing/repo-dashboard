from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from multi_repo_view.models import RepoDetail


class RepoDetailView(VerticalScroll):
    DEFAULT_CSS = """
    RepoDetailView {
        padding: 1 2;
    }

    RepoDetailView .repo-name {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }

    RepoDetailView .section-header {
        text-style: bold;
        color: $text;
        margin-top: 1;
        border-bottom: solid $surface;
    }

    RepoDetailView .pr-title {
        color: $success;
    }

    RepoDetailView .pr-url {
        color: $text-muted;
    }

    RepoDetailView .pr-status {
        padding-left: 2;
    }

    RepoDetailView .checks-passing {
        color: $success;
    }

    RepoDetailView .checks-failing {
        color: $error;
    }

    RepoDetailView .checks-pending {
        color: $warning;
    }

    RepoDetailView .branch-row {
        padding-left: 2;
    }

    RepoDetailView .branch-current {
        color: $success;
    }

    RepoDetailView .file-staged {
        color: $success;
        padding-left: 2;
    }

    RepoDetailView .file-modified {
        color: $warning;
        padding-left: 2;
    }

    RepoDetailView .file-untracked {
        color: $text-muted;
        padding-left: 2;
    }

    RepoDetailView .clean-state {
        color: $text-muted;
        padding-left: 2;
    }

    RepoDetailView .placeholder {
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._detail: RepoDetail | None = None

    def compose(self) -> ComposeResult:
        yield Static("Select a repository", classes="placeholder")

    def update_detail(self, detail: RepoDetail) -> None:
        self._detail = detail
        self._refresh_content()

    def _format_ahead_behind(self, ahead: int, behind: int) -> str:
        parts = []
        if ahead > 0:
            parts.append(f"↑{ahead}")
        if behind > 0:
            parts.append(f"↓{behind}")
        return " ".join(parts) if parts else ""

    def _format_checks_icon(self, status: str | None) -> str:
        match status:
            case "passing":
                return "✓"
            case "failing":
                return "✗"
            case "pending":
                return "○"
            case _:
                return ""

    def _refresh_content(self) -> None:
        self.remove_children()
        if not self._detail:
            self.mount(Static("Select a repository", classes="placeholder"))
            return

        detail = self._detail

        self.mount(Static(f"{detail.summary.name}", classes="repo-name"))

        if pr := detail.pr_info:
            self.mount(Static("Pull Request", classes="section-header"))
            checks_icon = self._format_checks_icon(pr.checks_status)
            checks_class = f"checks-{pr.checks_status}" if pr.checks_status else ""
            self.mount(Static(f"  #{pr.number} {pr.title}", classes="pr-title"))
            self.mount(Static(f"  {pr.url}", classes="pr-url"))
            status_parts = [pr.state]
            if checks_icon:
                status_parts.append(f"{checks_icon} {pr.checks_status}")
            self.mount(
                Static(
                    f"  {' | '.join(status_parts)}", classes=f"pr-status {checks_class}"
                )
            )

        self.mount(Static("Branches", classes="section-header"))
        for branch in detail.branches:
            marker = "* " if branch.is_current else "  "
            branch_class = "branch-current" if branch.is_current else ""
            ahead_behind = self._format_ahead_behind(branch.ahead, branch.behind)
            tracking_info = branch.tracking or "(local)"

            if ahead_behind:
                line = f"{marker}{branch.name:<24} {ahead_behind:<8} {tracking_info}"
            else:
                line = f"{marker}{branch.name:<24} {'—':<8} {tracking_info}"

            self.mount(Static(line, classes=f"branch-row {branch_class}"))

        self.mount(Static("Working Tree", classes="section-header"))

        has_changes = False

        for f in detail.staged_files:
            self.mount(Static(f"A  {f}", classes="file-staged"))
            has_changes = True

        for f in detail.modified_files:
            self.mount(Static(f"M  {f}", classes="file-modified"))
            has_changes = True

        for f in detail.untracked_files:
            self.mount(Static(f"?  {f}", classes="file-untracked"))
            has_changes = True

        if not has_changes:
            self.mount(
                Static("Nothing to commit, working tree clean", classes="clean-state")
            )

    @property
    def pr_url(self) -> str | None:
        if self._detail and self._detail.pr_info:
            return self._detail.pr_info.url
        return None
