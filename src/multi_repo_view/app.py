import asyncio
import webbrowser
from pathlib import Path
from textwrap import dedent

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from multi_repo_view.config import Config, _get_config_path, get_repo_paths, load_config
from multi_repo_view.git_ops import (
    get_branch_list_async,
    get_repo_summary_async,
    get_status_files_async,
)
from multi_repo_view.github_ops import get_pr_for_branch_async
from multi_repo_view.models import RepoDetail, RepoSummary
from multi_repo_view.widgets.repo_detail import RepoDetailView
from multi_repo_view.widgets.repo_list import RepoList


class MultiRepoViewApp(App):
    TITLE = "Multi-Repo View"

    CSS = """
    #main-container {
        height: 1fr;
    }

    #repo-list-panel {
        width: 1fr;
        border-right: solid $primary;
    }

    #repo-list-header {
        text-style: bold;
        padding: 1 2;
        background: $surface;
    }

    #empty-state {
        padding: 1 2;
        color: $text-muted;
    }

    #loading-state {
        padding: 1 2;
        color: $text-muted;
    }

    #filter-input {
        margin: 0 1;
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
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("/", "start_filter", "Filter", show=False),
        Binding("escape", "clear_filter", "Clear Filter", show=False),
        Binding("?", "help", "Help"),
    ]

    def __init__(self, config_path: Path | None = None, scan_path: Path | None = None) -> None:
        super().__init__()
        self._config_path = config_path
        self._scan_path = scan_path
        self._config: Config | None = None
        self._repo_paths: list[Path] = []
        self._summaries: list[RepoSummary] = []
        self._filter_active = False
        self._filter_text = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="repo-list-panel"):
                yield Static("Repositories", id="repo-list-header")
                yield Static("Loading...", id="loading-state")
            yield RepoDetailView()
        yield Footer()

    def on_mount(self) -> None:
        self._config = load_config(self._config_path)
        self._repo_paths = get_repo_paths(self._config, self._scan_path)
        self._load_summaries()
        if self._config:
            self.set_interval(
                self._config.settings.refresh_interval, self._refresh_data
            )

    def _load_summaries(self) -> None:
        self.run_worker(self._fetch_summaries(), exclusive=True, group="summaries")

    async def _fetch_summaries(self) -> list[RepoSummary]:
        summaries = await asyncio.gather(
            *[get_repo_summary_async(p) for p in self._repo_paths]
        )
        self._summaries = list(summaries)
        self._update_repo_list()
        return list(summaries)

    def _update_repo_list(self) -> None:
        panel = self.query_one("#repo-list-panel")

        loading = panel.query("#loading-state")
        for widget in loading:
            widget.remove()

        empty = panel.query("#empty-state")
        for widget in empty:
            widget.remove()

        repo_lists = panel.query(RepoList)
        for widget in repo_lists:
            widget.remove()

        if self._summaries:
            repo_list = RepoList(self._summaries)
            panel.mount(repo_list)
            repo_list.focus()
            self.call_after_refresh(self._select_first_repo)
        else:
            panel.mount(Static(self._get_empty_state_message(), id="empty-state"))

    def _get_empty_state_message(self) -> str:
        config_path = self._config_path or _get_config_path()
        return dedent(f"""\
            No repositories configured.

            Create a config file at:
            {config_path}

            Example config:
            [[repos]]
            path = "~/Developer/my-repo"

            [[repos]]
            path = "~/Projects/other-repo\"""")

    def _select_first_repo(self) -> None:
        try:
            repo_list = self.query_one(RepoList)
            if repo_list.index is None and len(repo_list) > 0:
                repo_list.index = 0
        except Exception:
            pass

    def _refresh_data(self) -> None:
        self._load_summaries()

    def on_repo_list_repo_selected(self, event: RepoList.RepoSelected) -> None:
        self.run_worker(
            self._fetch_repo_detail(event.summary),
            exclusive=True,
            group="detail",
        )

    async def _fetch_repo_detail(self, summary: RepoSummary) -> RepoDetail:
        branches, (untracked, modified, staged), pr_info = await asyncio.gather(
            get_branch_list_async(summary.path),
            get_status_files_async(summary.path),
            get_pr_for_branch_async(summary.path, summary.current_branch),
        )

        detail = RepoDetail(
            summary=summary,
            branches=branches,
            untracked_files=untracked,
            modified_files=modified,
            staged_files=staged,
            pr_info=pr_info,
        )

        self._update_detail_view(detail)
        return detail

    def _update_detail_view(self, detail: RepoDetail) -> None:
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

    def action_cursor_down(self) -> None:
        try:
            repo_list = self.query_one(RepoList)
            repo_list.action_cursor_down()
        except Exception:
            pass

    def action_cursor_up(self) -> None:
        try:
            repo_list = self.query_one(RepoList)
            repo_list.action_cursor_up()
        except Exception:
            pass

    def action_help(self) -> None:
        self.notify("j/k: Navigate | /: Filter | o: Open PR | r: Refresh | q: Quit")

    def action_start_filter(self) -> None:
        if not self._filter_active:
            self._filter_active = True
            panel = self.query_one("#repo-list-panel")
            header = self.query_one("#repo-list-header")
            filter_input = Input(placeholder="Filter repos...", id="filter-input")
            panel.mount(filter_input, after=header)
            filter_input.focus()

    def action_clear_filter(self) -> None:
        if self._filter_active:
            self._filter_active = False
            self._filter_text = ""
            try:
                filter_input = self.query_one("#filter-input", Input)
                filter_input.remove()
            except Exception:
                pass
            self._apply_filter()
            try:
                repo_list = self.query_one(RepoList)
                repo_list.focus()
            except Exception:
                pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._filter_text = event.value
            self._apply_filter()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            if event.value == "":
                self.action_clear_filter()
            else:
                try:
                    repo_list = self.query_one(RepoList)
                    repo_list.focus()
                    if len(repo_list) > 0:
                        repo_list.index = 0
                except Exception:
                    pass

    def _apply_filter(self) -> None:
        if not self._filter_text:
            filtered_summaries = self._summaries
        else:
            filter_lower = self._filter_text.lower()
            filtered_summaries = [
                s for s in self._summaries
                if filter_lower in s.name.lower() or filter_lower in s.current_branch.lower()
            ]

        try:
            repo_list = self.query_one(RepoList)
            repo_list.update_summaries(filtered_summaries)
        except Exception:
            pass
