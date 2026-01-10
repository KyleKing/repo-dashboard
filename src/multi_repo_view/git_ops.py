import asyncio
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


async def _run_git_async(path: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(path),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


def get_current_branch(path: Path) -> str:
    branch = _run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    return branch if branch else "HEAD"


async def get_current_branch_async(path: Path) -> str:
    branch = await _run_git_async(path, "rev-parse", "--abbrev-ref", "HEAD")
    return branch if branch else "HEAD"


def _get_uncommitted_count(path: Path) -> int:
    status = _run_git(path, "status", "--porcelain")
    return len(status.splitlines()) if status else 0


async def _get_uncommitted_count_async(path: Path) -> int:
    status = await _run_git_async(path, "status", "--porcelain")
    return len(status.splitlines()) if status else 0


def _parse_ahead_behind(output: str) -> tuple[int, int]:
    ahead = 0
    behind = 0
    if m := re.search(r"ahead (\d+)", output):
        ahead = int(m.group(1))
    if m := re.search(r"behind (\d+)", output):
        behind = int(m.group(1))
    return ahead, behind


def _get_ahead_behind(path: Path) -> tuple[int, int]:
    result = _run_git(path, "status", "--porcelain", "--branch")
    return _parse_ahead_behind(result)


async def _get_ahead_behind_async(path: Path) -> tuple[int, int]:
    result = await _run_git_async(path, "status", "--porcelain", "--branch")
    return _parse_ahead_behind(result)


def _parse_branch_list(output: str, current_branch: str) -> list[BranchInfo]:
    if not output:
        return []

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
                is_current=(name == current_branch),
                ahead=ahead,
                behind=behind,
                tracking=tracking,
            )
        )

    return sorted(branches, key=lambda b: (not b.is_current, b.name))


def get_branch_list(path: Path) -> list[BranchInfo]:
    output = _run_git(
        path,
        "for-each-ref",
        "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
        "refs/heads/",
    )
    current = get_current_branch(path)
    return _parse_branch_list(output, current)


async def get_branch_list_async(path: Path) -> list[BranchInfo]:
    output, current = await asyncio.gather(
        _run_git_async(
            path,
            "for-each-ref",
            "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
            "refs/heads/",
        ),
        get_current_branch_async(path),
    )
    return _parse_branch_list(output, current)


def _parse_status_files(output: str) -> tuple[list[str], list[str], list[str]]:
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


def get_status_files(path: Path) -> tuple[list[str], list[str], list[str]]:
    output = _run_git(path, "status", "--porcelain")
    return _parse_status_files(output)


async def get_status_files_async(path: Path) -> tuple[list[str], list[str], list[str]]:
    output = await _run_git_async(path, "status", "--porcelain")
    return _parse_status_files(output)


def get_repo_summary(path: Path) -> RepoSummary:
    ahead, behind = _get_ahead_behind(path)
    return RepoSummary(
        path=path,
        name=path.name,
        current_branch=get_current_branch(path),
        ahead_count=ahead,
        behind_count=behind,
        uncommitted_count=_get_uncommitted_count(path),
    )


async def get_repo_summary_async(path: Path) -> RepoSummary:
    current_branch, (ahead, behind), uncommitted = await asyncio.gather(
        get_current_branch_async(path),
        _get_ahead_behind_async(path),
        _get_uncommitted_count_async(path),
    )
    return RepoSummary(
        path=path,
        name=path.name,
        current_branch=current_branch,
        ahead_count=ahead,
        behind_count=behind,
        uncommitted_count=uncommitted,
    )
