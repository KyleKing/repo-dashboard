from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoSummary:
    path: Path
    name: str
    current_branch: str
    has_unpushed: bool
    has_uncommitted: bool


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
