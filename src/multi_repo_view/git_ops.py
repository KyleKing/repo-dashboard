import re
import subprocess
from pathlib import Path

from multi_repo_view.models import BranchInfo, RepoSummary


def _run_git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_current_branch(path: Path) -> str:
    branch = _run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    return branch if branch else "HEAD"


def _has_uncommitted_changes(path: Path) -> bool:
    status = _run_git(path, "status", "--porcelain")
    return bool(status)


def _has_unpushed_commits(path: Path) -> bool:
    result = _run_git(path, "status", "--porcelain", "--branch")
    return "ahead" in result


def get_branch_list(path: Path) -> list[BranchInfo]:
    output = _run_git(
        path,
        "for-each-ref",
        "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
        "refs/heads/",
    )
    if not output:
        return []

    current = get_current_branch(path)
    branches: list[BranchInfo] = []

    for line in output.splitlines():
        parts = line.split("|")
        name = parts[0]
        tracking = parts[1] if len(parts) > 1 and parts[1] else None
        track_info = parts[2] if len(parts) > 2 else ""

        ahead = 0
        behind = 0
        if track_info:
            if m := re.search(r"ahead (\d+)", track_info):
                ahead = int(m.group(1))
            if m := re.search(r"behind (\d+)", track_info):
                behind = int(m.group(1))

        branches.append(
            BranchInfo(
                name=name,
                is_current=(name == current),
                ahead=ahead,
                behind=behind,
                tracking=tracking,
            )
        )

    return sorted(branches, key=lambda b: (not b.is_current, b.name))


def get_status_files(path: Path) -> tuple[list[str], list[str], list[str]]:
    output = _run_git(path, "status", "--porcelain")
    untracked: list[str] = []
    modified: list[str] = []
    staged: list[str] = []

    for line in output.splitlines():
        if len(line) < 3:
            continue
        index_status = line[0]
        worktree_status = line[1]
        filename = line[3:]

        if index_status == "?" and worktree_status == "?":
            untracked.append(filename)
        elif index_status != " " and index_status != "?":
            staged.append(filename)
        if worktree_status != " " and worktree_status != "?":
            modified.append(filename)

    return untracked, modified, staged


def get_repo_summary(path: Path) -> RepoSummary:
    return RepoSummary(
        path=path,
        name=path.name,
        current_branch=get_current_branch(path),
        has_unpushed=_has_unpushed_commits(path),
        has_uncommitted=_has_uncommitted_changes(path),
    )
