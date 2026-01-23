from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

VCSType = Literal["git", "jj"]


class ItemKind(StrEnum):
    BRANCH = "branch"
    STASH = "stash"
    WORKTREE = "worktree"


class RepoStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    NO_GIT = "no_git"
    NO_JJ = "no_jj"
    NO_GH = "no_gh"
    NO_UPSTREAM = "no_upstream"
    DETACHED_HEAD = "detached_head"
    LOADING = "loading"


class FilterMode(StrEnum):
    ALL = "all"
    AHEAD = "ahead"
    BEHIND = "behind"
    DIRTY = "dirty"
    HAS_PR = "has_pr"
    HAS_STASH = "has_stash"


@dataclass(frozen=True)
class ActiveFilter:
    mode: FilterMode
    inverted: bool = False

    @property
    def display_name(self) -> str:
        name = self.mode.value.replace("_", " ")
        return f"not {name}" if self.inverted else name

    @property
    def short_key(self) -> str:
        match self.mode:
            case FilterMode.AHEAD:
                return "a"
            case FilterMode.BEHIND:
                return "b"
            case FilterMode.DIRTY:
                return "d"
            case FilterMode.HAS_PR:
                return "p"
            case FilterMode.HAS_STASH:
                return "s"
            case _:
                return ""


class SortMode(StrEnum):
    NAME = "name"
    MODIFIED = "modified"
    STATUS = "status"
    BRANCH = "branch"


@dataclass(frozen=True)
class RepoSummary:
    path: Path
    name: str
    vcs_type: VCSType
    current_branch: str
    ahead_count: int
    behind_count: int
    uncommitted_count: int
    stash_count: int
    worktree_count: int
    pr_info: "PRInfo | None"
    last_modified: datetime
    status: RepoStatus
    jj_is_colocated: bool | None = None
    jj_working_copy_id: str | None = None

    @property
    def is_dirty(self) -> bool:
        return self.ahead_count > 0 or self.uncommitted_count > 0

    @property
    def status_summary(self) -> str:
        parts = []
        if self.ahead_count > 0:
            parts.append(f"↑{self.ahead_count}")
        if self.behind_count > 0:
            parts.append(f"↓{self.behind_count}")
        if self.uncommitted_count > 0:
            parts.append(f"*{self.uncommitted_count}")
        if self.stash_count > 0:
            parts.append(f"${self.stash_count}")
        if self.worktree_count > 0:
            parts.append(f"W{self.worktree_count}")
        return " ".join(parts) if parts else "clean"

    @property
    def warning_message(self) -> str | None:
        """Get human-readable warning message based on status"""
        match self.status:
            case RepoStatus.OK | RepoStatus.LOADING:
                return None
            case RepoStatus.NO_GIT:
                return "Git not installed"
            case RepoStatus.NO_JJ:
                return "Jujutsu (jj) not installed"
            case RepoStatus.NO_GH:
                return "GitHub CLI (gh) not installed"
            case RepoStatus.NO_UPSTREAM:
                return "No upstream configured"
            case RepoStatus.DETACHED_HEAD:
                return "Detached HEAD state"
            case RepoStatus.WARNING:
                return "Unknown issue"
            case _:
                return None


@dataclass(frozen=True)
class BranchInfo:
    name: str
    is_current: bool
    ahead: int
    behind: int
    tracking: str | None


@dataclass(frozen=True)
class PRInfo:
    number: int
    title: str
    url: str
    state: str
    checks_status: str | None


@dataclass(frozen=True)
class RepoDetail:
    summary: RepoSummary
    branches: list[BranchInfo]
    untracked_files: list[str]
    modified_files: list[str]
    staged_files: list[str]
    pr_info: PRInfo | None


@dataclass(frozen=True)
class RepoItem:
    kind: ItemKind
    name: str
    display_name: str
    ahead: int
    behind: int
    uncommitted: int
    reference: str | None
    pr_info: PRInfo | None

    @property
    def status_summary(self) -> str:
        parts = []
        if self.ahead > 0:
            parts.append(f"↑{self.ahead}")
        if self.behind > 0:
            parts.append(f"↓{self.behind}")
        if self.uncommitted > 0:
            parts.append(f"*{self.uncommitted}")
        return " ".join(parts) if parts else "—"


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    message: str
    author: str
    date: datetime

    @property
    def relative_time(self) -> str:
        date_naive = self.date.replace(tzinfo=None) if self.date.tzinfo else self.date
        delta = datetime.now() - date_naive
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = delta.seconds // 60
        return f"{minutes}m ago"


@dataclass(frozen=True)
class PRDetail:
    number: int
    title: str
    url: str
    state: str
    checks_status: str | None
    description: str
    unresolved_comments: int
    additions: int
    deletions: int


@dataclass(frozen=True)
class BranchDetail:
    branch_info: BranchInfo
    pr_detail: PRDetail | None
    commits_ahead: list[CommitInfo]
    commits_behind: list[CommitInfo]
    modified_files: list[str]
    staged_files: list[str]
    untracked_files: list[str]


@dataclass(frozen=True)
class StashDetail:
    name: str
    message: str
    branch: str
    modified_files: list[str]
    date: datetime


@dataclass(frozen=True)
class WorktreeInfo:
    """Git worktree or JJ workspace information"""

    path: Path
    branch: str | None
    commit: str | None
    is_main: bool
    is_detached: bool = False
    is_locked: bool = False
