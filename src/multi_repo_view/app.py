import webbrowser
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from multi_repo_view.config import Config, get_repo_paths, load_config
from multi_repo_view.git_ops import get_branch_list, get_repo_summary, get_status_files
from multi_repo_view.github_ops import get_pr_for_branch
from multi_repo_view.models import RepoDetail, RepoSummary
from multi_repo_view.widgets.repo_detail import RepoDetailView
from multi_repo_view.widgets.repo_list import RepoList


class MultiRepoViewApp(App):
    TITLE = "Multi-Repo View"

    CSS = """
    #main-container {
        height: 1fr;
    }

    #repo-list-container {
        width: 1fr;
        border-right: solid $primary;
    }

    #repo-list-header {
        text-style: bold;
        padding: 1 2;
        background: $surface;
    }

    RepoList {
        height: 1fr;
    }

    RepoDetailView {
        width: 2fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_pr", "Open PR"),
        Binding("?", "help", "Help"),
    ]

    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__()
        self._config_path = config_path
        self._config: Config | None = None
        self._repo_paths: list[Path] = []
        self._summaries: list[RepoSummary] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            with Horizontal(id="repo-list-container"):
                yield Static("Repositories", id="repo-list-header")
            yield RepoDetailView()
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()
        self._mount_repo_list()
        if self._config:
            self.set_interval(self._config.settings.refresh_interval, self._refresh_data)

    def _load_data(self) -> None:
        self._config = load_config(self._config_path)
        self._repo_paths = get_repo_paths(self._config)
        self._summaries = [get_repo_summary(p) for p in self._repo_paths]

    def _mount_repo_list(self) -> None:
        container = self.query_one("#repo-list-container")
        if self._summaries:
            repo_list = RepoList(self._summaries)
            container.mount(repo_list)

    def _refresh_data(self) -> None:
        self._summaries = [get_repo_summary(p) for p in self._repo_paths]
        try:
            repo_list = self.query_one(RepoList)
            repo_list.update_summaries(self._summaries)
        except Exception:
            pass

    def on_repo_list_repo_selected(self, event: RepoList.RepoSelected) -> None:
        summary = event.summary
        branches = get_branch_list(summary.path)
        untracked, modified, staged = get_status_files(summary.path)
        pr_info = get_pr_for_branch(summary.path, summary.current_branch)

        detail = RepoDetail(
            summary=summary,
            branches=branches,
            untracked_files=untracked,
            modified_files=modified,
            staged_files=staged,
            pr_info=pr_info,
        )

        detail_view = self.query_one(RepoDetailView)
        detail_view.update_detail(detail)

    def action_refresh(self) -> None:
        self._refresh_data()
        self.notify("Refreshed")

    def action_open_pr(self) -> None:
        detail_view = self.query_one(RepoDetailView)
        if url := detail_view.pr_url:
            webbrowser.open(url)
            self.notify(f"Opening {url}")
        else:
            self.notify("No PR for current branch", severity="warning")

    def action_help(self) -> None:
        self.notify("j/k: Navigate | o: Open PR | r: Refresh | q: Quit")
