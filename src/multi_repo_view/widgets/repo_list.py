from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from multi_repo_view.models import RepoSummary


class RepoListItem(ListItem):
    DEFAULT_CSS = """
    RepoListItem {
        padding: 0 1;
    }
    """

    def __init__(self, summary: RepoSummary) -> None:
        super().__init__()
        self.summary = summary

    def _format_status_indicators(self) -> str:
        parts = []
        if self.summary.ahead_count > 0:
            parts.append(f"↑{self.summary.ahead_count}")
        if self.summary.behind_count > 0:
            parts.append(f"↓{self.summary.behind_count}")
        if self.summary.uncommitted_count > 0:
            parts.append(f"*{self.summary.uncommitted_count}")
        return " ".join(parts)

    def compose(self) -> ComposeResult:
        status = self._format_status_indicators()
        yield Static(f"{status:<8} {self.summary.name:<16} {self.summary.current_branch}")


class RepoList(ListView):
    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    class RepoSelected(Message):
        def __init__(self, summary: RepoSummary) -> None:
            super().__init__()
            self.summary = summary

    def __init__(self, summaries: list[RepoSummary]) -> None:
        super().__init__()
        self._summaries = summaries

    def compose(self) -> ComposeResult:
        for summary in self._summaries:
            yield RepoListItem(summary)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, RepoListItem):
            self.post_message(self.RepoSelected(event.item.summary))

    def update_summaries(self, summaries: list[RepoSummary]) -> None:
        self._summaries = summaries
        self.clear()
        for summary in summaries:
            self.append(RepoListItem(summary))
