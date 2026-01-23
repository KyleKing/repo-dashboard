import asyncio
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from repo_dashboard.cache import branch_cache, commit_cache
from repo_dashboard.models import (
    BranchInfo,
    CommitInfo,
    RepoStatus,
    RepoSummary,
    StashDetail,
    WorktreeInfo,
)


def _check_git_installed() -> bool:
    """Check if git is installed and available"""
    return shutil.which("git") is not None


def _run_git(path: Path, *args: str) -> str:
    if not _check_git_installed():
        raise FileNotFoundError("git command not found - please install git")

    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


async def _run_git_async(path: Path, *args: str) -> str:
    if not _check_git_installed():
        raise FileNotFoundError("git command not found - please install git")

    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(path),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip()


def _is_detached_head(path: Path) -> bool:
    """Check if repository is in detached HEAD state"""
    try:
        result = _run_git(path, "symbolic-ref", "-q", "HEAD")
        return not result
    except Exception:
        return True


async def _is_detached_head_async(path: Path) -> bool:
    """Check if repository is in detached HEAD state"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(path),
            "symbolic-ref",
            "-q",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode != 0
    except Exception:
        return True


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
    cache_key = f"{path}:branches"
    if cached := branch_cache.get(cache_key):
        return cached

    output, current = await asyncio.gather(
        _run_git_async(
            path,
            "for-each-ref",
            "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
            "refs/heads/",
        ),
        get_current_branch_async(path),
    )
    result = _parse_branch_list(output, current)
    branch_cache.set(cache_key, result)
    return result


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
    try:
        last_commit = _run_git(path, "log", "-1", "--format=%ai")
        last_modified = (
            datetime.fromisoformat(last_commit) if last_commit else datetime.now()
        )
    except Exception:
        last_modified = datetime.now()

    return RepoSummary(
        path=path,
        name=path.name,
        vcs_type="git",
        current_branch=get_current_branch(path),
        ahead_count=ahead,
        behind_count=behind,
        uncommitted_count=_get_uncommitted_count(path),
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=last_modified,
        status=RepoStatus.OK,
    )


async def get_repo_summary_async(path: Path) -> RepoSummary:
    try:
        (
            current_branch,
            is_detached,
            (ahead, behind),
            uncommitted,
            last_modified,
            stash_count,
            worktree_count,
        ) = await asyncio.gather(
            get_current_branch_async(path),
            _is_detached_head_async(path),
            _get_ahead_behind_async(path),
            _get_uncommitted_count_async(path),
            get_last_modified_time(path),
            get_stash_count(path),
            get_worktree_count(path),
        )

        status = RepoStatus.OK
        if is_detached:
            status = RepoStatus.DETACHED_HEAD
        elif ahead == 0 and behind == 0:
            tracking = await _get_tracking_branch(path, current_branch)
            if not tracking:
                status = RepoStatus.NO_UPSTREAM

        return RepoSummary(
            path=path,
            name=path.name,
            vcs_type="git",
            current_branch=current_branch,
            ahead_count=ahead,
            behind_count=behind,
            uncommitted_count=uncommitted,
            stash_count=stash_count,
            worktree_count=worktree_count,
            pr_info=None,
            last_modified=last_modified,
            status=status,
        )
    except FileNotFoundError:
        return RepoSummary(
            path=path,
            name=path.name,
            vcs_type="git",
            current_branch="?",
            ahead_count=0,
            behind_count=0,
            uncommitted_count=0,
            stash_count=0,
            worktree_count=0,
            pr_info=None,
            last_modified=datetime.now(),
            status=RepoStatus.NO_GIT,
        )
    except Exception:
        return RepoSummary(
            path=path,
            name=path.name,
            vcs_type="git",
            current_branch="?",
            ahead_count=0,
            behind_count=0,
            uncommitted_count=0,
            stash_count=0,
            worktree_count=0,
            pr_info=None,
            last_modified=datetime.now(),
            status=RepoStatus.WARNING,
        )


async def get_worktree_count(path: Path) -> int:
    """Get count of git worktrees (simple detection)"""
    cache_key = f"{path}:worktree_count"
    if cached := commit_cache.get(cache_key):
        return cached

    output = await _run_git_async(path, "worktree", "list", "--porcelain")
    count = len([line for line in output.splitlines() if line.startswith("worktree ")])
    result = max(0, count - 1)
    commit_cache.set(cache_key, result)
    return result


async def get_worktree_list(path: Path) -> list[WorktreeInfo]:
    """Get list of all worktrees"""
    cache_key = f"{path}:worktrees"
    if cached := commit_cache.get(cache_key):
        return cached

    output = await _run_git_async(path, "worktree", "list", "--porcelain")

    worktrees = []
    current = {}
    worktree_index = 0

    for line in output.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(_parse_worktree(current, is_main=(worktree_index == 0)))
                worktree_index += 1
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("HEAD "):
            current["commit"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line.startswith("detached"):
            current["detached"] = True
        elif line.startswith("locked"):
            current["locked"] = True

    if current:
        worktrees.append(_parse_worktree(current, is_main=(worktree_index == 0)))

    result = worktrees[1:] if len(worktrees) > 1 else []
    commit_cache.set(cache_key, result)
    return result


def _parse_worktree(data: dict, is_main: bool = False) -> WorktreeInfo:
    return WorktreeInfo(
        path=Path(data["path"]),
        branch=data.get("branch"),
        commit=data.get("commit"),
        is_main=is_main,
        is_detached=data.get("detached", False),
        is_locked=data.get("locked", False),
    )


async def get_stash_count(path: Path) -> int:
    """Get count of stashes"""
    cache_key = f"{path}:stash_count"
    if cached := commit_cache.get(cache_key):
        return cached

    output = await _run_git_async(path, "stash", "list")
    count = len(output.splitlines()) if output else 0
    commit_cache.set(cache_key, count)
    return count


async def get_stash_list(path: Path) -> list[dict]:
    """Get list of stashes (lazy loaded)"""
    cache_key = f"{path}:stashes"
    if cached := commit_cache.get(cache_key):
        return cached

    output = await _run_git_async(
        path,
        "stash",
        "list",
        "--format=%gd|%gs|%gD|%cr",
    )

    stashes = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            stashes.append(
                {
                    "name": parts[0],
                    "message": parts[1],
                    "reflog": parts[2],
                    "time": parts[3],
                }
            )

    commit_cache.set(cache_key, stashes)
    return stashes


async def get_stash_detail(path: Path, stash_name: str) -> StashDetail:
    """Get detailed stash information"""
    info_output = await _run_git_async(
        path,
        "log",
        "-1",
        "--format=%ai|%s",
        stash_name,
    )

    parts = info_output.strip().split("|", 1)
    date_str = parts[0] if parts else ""
    message = parts[1] if len(parts) > 1 else ""

    files_output = await _run_git_async(
        path,
        "stash",
        "show",
        "--name-only",
        stash_name,
    )

    branch = message.replace("WIP on ", "").replace("On ", "").split(":")[0].strip()

    return StashDetail(
        name=stash_name,
        message=message,
        branch=branch,
        modified_files=files_output.splitlines(),
        date=datetime.fromisoformat(date_str) if date_str else datetime.now(),
    )


async def get_commits_ahead(path: Path, branch: str) -> list[CommitInfo]:
    """Get commits ahead of tracking branch"""
    cache_key = f"{path}:{branch}:ahead"
    if cached := commit_cache.get(cache_key):
        return cached

    tracking = await _get_tracking_branch(path, branch)
    if not tracking:
        return []

    output = await _run_git_async(
        path,
        "log",
        f"{tracking}..{branch}",
        "--format=%h|%s|%an|%ai",
    )

    result = _parse_commit_list(output)
    commit_cache.set(cache_key, result)
    return result


async def get_commits_behind(path: Path, branch: str) -> list[CommitInfo]:
    """Get commits behind tracking branch"""
    cache_key = f"{path}:{branch}:behind"
    if cached := commit_cache.get(cache_key):
        return cached

    tracking = await _get_tracking_branch(path, branch)
    if not tracking:
        return []

    output = await _run_git_async(
        path,
        "log",
        f"{branch}..{tracking}",
        "--format=%h|%s|%an|%ai",
    )

    result = _parse_commit_list(output)
    commit_cache.set(cache_key, result)
    return result


def _parse_commit_list(output: str) -> list[CommitInfo]:
    commits = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                CommitInfo(
                    sha=parts[0],
                    message=parts[1],
                    author=parts[2],
                    date=datetime.fromisoformat(parts[3]),
                )
            )
    return commits


async def _get_tracking_branch(path: Path, branch: str) -> str | None:
    """Get tracking branch for given branch"""
    try:
        output = await _run_git_async(
            path,
            "rev-parse",
            "--abbrev-ref",
            f"{branch}@{{upstream}}",
        )
        return output if output else None
    except Exception:
        return None


async def get_last_modified_time(path: Path) -> datetime:
    """Get last commit or modification time"""
    output = await _run_git_async(path, "log", "-1", "--format=%ai")
    if output:
        return datetime.fromisoformat(output)
    return datetime.fromtimestamp(path.stat().st_mtime)


async def get_upstream_repo(path: Path) -> str | None:
    """Get upstream repo identifier (e.g., 'owner/repo')"""
    output = await _run_git_async(path, "remote", "get-url", "origin")
    if not output:
        return None

    if m := re.search(r"github\.com[:/](.+?)(?:\.git)?$", output):
        return m.group(1)

    return None


async def get_branch_detail_async(
    path: Path,
    branch_name: str,
    pr_detail: "PRDetail | None" = None,
) -> "BranchDetail":
    """Aggregate all branch detail data in parallel"""
    from repo_dashboard.models import BranchDetail

    branches = await get_branch_list_async(path)
    branch_info = next((b for b in branches if b.name == branch_name), None)

    if not branch_info:
        raise ValueError(f"Branch {branch_name} not found")

    commits_ahead, commits_behind, (untracked, modified, staged) = await asyncio.gather(
        get_commits_ahead(path, branch_name),
        get_commits_behind(path, branch_name),
        get_status_files_async(path),
    )

    return BranchDetail(
        branch_info=branch_info,
        pr_detail=pr_detail,
        commits_ahead=commits_ahead,
        commits_behind=commits_behind,
        modified_files=modified,
        staged_files=staged,
        untracked_files=untracked,
    )
