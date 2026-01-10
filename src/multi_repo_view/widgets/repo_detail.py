from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Rule, Static

from multi_repo_view.models import RepoDetail


class RepoDetailView(VerticalScroll):
    DEFAULT_CSS = """
    RepoDetailView {
        padding: 1 2;
    }

    RepoDetailView .section-title {
        text-style: bold;
        margin-top: 1;
    }

    RepoDetailView .pr-title {
        color: $accent;
    }

    RepoDetailView .pr-url {
        color: $text-muted;
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

    RepoDetailView .branch-current {
        text-style: bold;
    }

    RepoDetailView .file-list {
        padding-left: 2;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._detail: RepoDetail | None = None

    def compose(self) -> ComposeResult:
        yield Static("Select a repository", id="placeholder")

    def update_detail(self, detail: RepoDetail) -> None:
        self._detail = detail
        self._refresh_content()

    def _refresh_content(self) -> None:
        self.remove_children()
        if not self._detail:
            self.mount(Static("Select a repository", id="placeholder"))
            return

        detail = self._detail
        self.mount(Static(detail.summary.name, classes="section-title"))
        self.mount(Rule())

        if pr := detail.pr_info:
            self.mount(Static(f"PR #{pr.number}: {pr.title}", classes="pr-title"))
            self.mount(Static(pr.url, classes="pr-url"))
            checks_class = f"checks-{pr.checks_status}" if pr.checks_status else ""
            status_text = f"Status: {pr.state}"
            if pr.checks_status:
                status_text += f"  Checks: {pr.checks_status}"
            self.mount(Static(status_text, classes=checks_class))
            self.mount(Rule())

        self.mount(Static("Branches", classes="section-title"))
        for branch in detail.branches:
            marker = "*" if branch.is_current else " "
            tracking = branch.tracking or "(local only)"
            ahead_behind = ""
            if branch.tracking:
                ahead_behind = f" [{branch.ahead}/{branch.behind}]"
            branch_class = "branch-current" if branch.is_current else ""
            self.mount(Static(f"  {marker} {branch.name:<25}{ahead_behind:<10} {tracking}", classes=branch_class))

        self.mount(Rule())
        self.mount(Static("Working Tree", classes="section-title"))

        if detail.staged_files:
            self.mount(Static("Staged:"))
            for f in detail.staged_files:
                self.mount(Static(f"  {f}", classes="file-list"))

        if detail.modified_files:
            self.mount(Static("Modified:"))
            for f in detail.modified_files:
                self.mount(Static(f"  {f}", classes="file-list"))

        if detail.untracked_files:
            self.mount(Static("Untracked:"))
            for f in detail.untracked_files:
                self.mount(Static(f"  {f}", classes="file-list"))

        if not any([detail.staged_files, detail.modified_files, detail.untracked_files]):
            self.mount(Static("  (clean)", classes="file-list"))

    @property
    def pr_url(self) -> str | None:
        if self._detail and self._detail.pr_info:
            return self._detail.pr_info.url
        return None
