from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from multi_repo_view.models import RepoSummary


class RepoListItem(ListItem):
    def __init__(self, summary: RepoSummary) -> None:
        super().__init__()
        self.summary = summary

    def compose(self) -> ComposeResult:
        indicator = "[*]" if self.summary.has_unpushed or self.summary.has_uncommitted else "[ ]"
        yield Static(f"{indicator} {self.summary.name:<20} {self.summary.current_branch}")


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
