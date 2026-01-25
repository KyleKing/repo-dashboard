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
    VCSType,
    WorktreeInfo,
)


class JJOperations:
    """JJ (Jujutsu) implementation of VCS operations"""

    vcs_type: VCSType = "jj"

    def __init__(self) -> None:
        self._is_colocated_cache: dict[Path, bool] = {}

    def _check_jj_installed(self) -> bool:
        """Check if jj is installed and available"""
        return shutil.which("jj") is not None

    def _is_colocated(self, repo_path: Path) -> bool:
        """Check if jj repo is colocated with git"""
        if repo_path in self._is_colocated_cache:
            return self._is_colocated_cache[repo_path]

        is_col = (repo_path / ".git").is_dir()
        self._is_colocated_cache[repo_path] = is_col
        return is_col

    def _get_git_dir(self, repo_path: Path) -> str:
        """Get GIT_DIR for gh CLI integration"""
        if self._is_colocated(repo_path):
            return str(repo_path / ".git")
        return str(repo_path / ".jj" / "repo" / "store" / "git")

    def _run_jj(self, path: Path, *args: str) -> str:
        """Run jj command synchronously"""
        if not self._check_jj_installed():
            raise FileNotFoundError("jj command not found - please install jujutsu")

        result = subprocess.run(
            ["jj", "-R", str(path), *args],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    async def _run_jj_async(self, path: Path, *args: str) -> str:
        """Run jj command asynchronously"""
        if not self._check_jj_installed():
            raise FileNotFoundError("jj command not found - please install jujutsu")

        proc = await asyncio.create_subprocess_exec(
            "jj",
            "-R",
            str(path),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode().strip()

    def get_current_branch(self, repo_path: Path) -> str:
        """Get current bookmark (jj equivalent of branch)"""
        output = self._run_jj(repo_path, "log", "-r", "@", "-T", "bookmarks")
        bookmarks = output.strip()
        if bookmarks:
            return bookmarks.split()[0]
        return "@"

    async def get_current_branch_async(self, repo_path: Path) -> str:
        """Get current bookmark asynchronously"""
        output = await self._run_jj_async(repo_path, "log", "-r", "@", "-T", "bookmarks")
        bookmarks = output.strip()
        if bookmarks:
            return bookmarks.split()[0]
        return "@"

    async def _get_uncommitted_count_async(self, repo_path: Path) -> int:
        """Deprecated: Get count of modified files in working copy"""
        output = await self._run_jj_async(repo_path, "status")
        lines = [line for line in output.splitlines() if line.startswith("Working copy changes:")]
        if not lines:
            return 0
        count = 0
        for line in output.splitlines():
            if line.startswith(("A ", "M ", "D ", "R ")):
                count += 1
        return count

    async def _get_status_counts_async(self, repo_path: Path) -> tuple[int, int, int]:
        """Returns (staged_count, unstaged_count, untracked_count)

        For jj:
        - staged = 0 (no staging concept)
        - unstaged = modified files in working copy (A, M, D, R)
        - untracked = 0 (jj tracks all files in working copy)
        """
        output = await self._run_jj_async(repo_path, "status")
        lines = [line for line in output.splitlines() if line.startswith("Working copy changes:")]
        if not lines:
            return (0, 0, 0)

        unstaged_count = 0
        for line in output.splitlines():
            if line.startswith(("A ", "M ", "D ", "R ")):
                unstaged_count += 1

        return (0, unstaged_count, 0)

    def _parse_ahead_behind(self, repo_path: Path, bookmark: str) -> tuple[int, int]:
        """Parse ahead/behind for a bookmark"""
        try:
            tracking = self._run_jj(
                repo_path,
                "log",
                "-r",
                f"{bookmark}@origin..",
                "-T",
                "commit_id",
            )
            ahead = len([line for line in tracking.splitlines() if line.strip()])

            tracking_behind = self._run_jj(
                repo_path,
                "log",
                "-r",
                f"..{bookmark}@origin",
                "-T",
                "commit_id",
            )
            behind = len([line for line in tracking_behind.splitlines() if line.strip()])

            return ahead, behind
        except Exception:
            return 0, 0

    async def _check_tracking_exists(self, repo_path: Path, bookmark: str) -> bool:
        """Check if bookmark has a tracking remote"""
        try:
            output = await self._run_jj_async(repo_path, "bookmark", "list")
            for line in output.splitlines():
                if line.strip().startswith(bookmark):
                    return ":" in line and "@origin" in line
            return False
        except Exception:
            return False

    async def _get_ahead_behind_async(self, repo_path: Path, bookmark: str) -> tuple[int, int]:
        """Get ahead/behind counts asynchronously"""
        try:
            tracking = await self._run_jj_async(
                repo_path,
                "log",
                "-r",
                f"{bookmark}@origin..",
                "-T",
                "commit_id",
            )
            ahead = len([line for line in tracking.splitlines() if line.strip()])

            tracking_behind = await self._run_jj_async(
                repo_path,
                "log",
                "-r",
                f"..{bookmark}@origin",
                "-T",
                "commit_id",
            )
            behind = len([line for line in tracking_behind.splitlines() if line.strip()])

            return ahead, behind
        except Exception:
            return 0, 0

    def _parse_branch_list(self, output: str, current_bookmark: str) -> list[BranchInfo]:
        """Parse jj bookmark list output"""
        if not output:
            return []

        branches: list[BranchInfo] = []
        for line in output.splitlines():
            if not line.strip():
                continue

            parts = line.split(":")
            if len(parts) < 2:
                continue

            name = parts[0].strip()
            tracking_info = parts[1].strip() if len(parts) > 1 else None

            tracking = f"{name}@origin" if tracking_info else None
            ahead, behind = self._parse_ahead_behind(Path("."), name) if tracking_info else (0, 0)

            branches.append(
                BranchInfo(
                    name=name,
                    is_current=(name == current_bookmark),
                    ahead=ahead,
                    behind=behind,
                    tracking=tracking,
                )
            )

        return sorted(branches, key=lambda b: (not b.is_current, b.name))

    async def get_branch_list_async(self, repo_path: Path) -> list[BranchInfo]:
        """Get list of bookmarks (jj equivalent of branches)"""
        cache_key = f"{repo_path}:branches"
        if cached := branch_cache.get(cache_key):
            return cached

        output = await self._run_jj_async(repo_path, "bookmark", "list")
        current = await self.get_current_branch_async(repo_path)
        result = self._parse_branch_list(output, current)
        branch_cache.set(cache_key, result)
        return result

    async def get_status_files_async(self, repo_path: Path) -> tuple[list[str], list[str], list[str]]:
        """Get untracked, modified, and staged files"""
        output = await self._run_jj_async(repo_path, "status")

        untracked: list[str] = []
        modified: list[str] = []
        staged: list[str] = []

        for line in output.splitlines():
            if line.startswith("A "):
                modified.append(line[2:].strip())
            elif line.startswith("M "):
                modified.append(line[2:].strip())
            elif line.startswith("D "):
                modified.append(line[2:].strip())
            elif line.startswith("R "):
                modified.append(line[2:].strip())

        return untracked, modified, staged

    def get_repo_summary(self, repo_path: Path) -> RepoSummary:
        """Get repository summary synchronously"""
        current_bookmark = self.get_current_branch(repo_path)
        ahead, behind = self._parse_ahead_behind(repo_path, current_bookmark)

        try:
            last_commit = self._run_jj(repo_path, "log", "-r", "@", "-T", "committer_date")
            last_modified = datetime.fromisoformat(last_commit) if last_commit else datetime.now()
        except Exception:
            last_modified = datetime.now()

        return RepoSummary(
            path=repo_path,
            name=repo_path.name,
            vcs_type="jj",
            current_branch=current_bookmark,
            ahead_count=ahead,
            behind_count=behind,
            staged_count=0,
            unstaged_count=0,
            untracked_count=0,
            stash_count=0,
            worktree_count=0,
            pr_info=None,
            last_modified=last_modified,
            status=RepoStatus.OK,
            has_remote=True,
            jj_is_colocated=self._is_colocated(repo_path),
        )

    async def get_repo_summary_async(self, repo_path: Path) -> RepoSummary:
        """Get repository summary asynchronously"""
        try:
            current_bookmark = await self.get_current_branch_async(repo_path)
            ahead, behind = await self._get_ahead_behind_async(repo_path, current_bookmark)
            staged, unstaged, untracked = await self._get_status_counts_async(repo_path)
            worktree_count = await self.get_worktree_count(repo_path)

            try:
                last_commit = await self._run_jj_async(repo_path, "log", "-r", "@", "-T", "committer_date")
                last_modified = datetime.fromisoformat(last_commit) if last_commit else datetime.now()
            except Exception:
                last_modified = datetime.now()

            status = RepoStatus.OK
            has_remote = True
            if ahead == 0 and behind == 0 and current_bookmark != "@":
                upstream_exists = await self._check_tracking_exists(repo_path, current_bookmark)
                if not upstream_exists:
                    status = RepoStatus.NO_UPSTREAM
                    has_remote = False
            elif current_bookmark != "@":
                upstream_exists = await self._check_tracking_exists(repo_path, current_bookmark)
                has_remote = upstream_exists

            return RepoSummary(
                path=repo_path,
                name=repo_path.name,
                vcs_type="jj",
                current_branch=current_bookmark,
                ahead_count=ahead,
                behind_count=behind,
                staged_count=staged,
                unstaged_count=unstaged,
                untracked_count=untracked,
                stash_count=0,
                worktree_count=worktree_count,
                pr_info=None,
                last_modified=last_modified,
                status=status,
                has_remote=has_remote,
                jj_is_colocated=self._is_colocated(repo_path),
            )
        except FileNotFoundError:
            return RepoSummary(
                path=repo_path,
                name=repo_path.name,
                vcs_type="jj",
                current_branch="?",
                ahead_count=0,
                behind_count=0,
                staged_count=0,
                unstaged_count=0,
                untracked_count=0,
                stash_count=0,
                worktree_count=0,
                pr_info=None,
                last_modified=datetime.now(),
                status=RepoStatus.NO_JJ,
                has_remote=False,
            )
        except Exception:
            return RepoSummary(
                path=repo_path,
                name=repo_path.name,
                vcs_type="jj",
                current_branch="?",
                ahead_count=0,
                behind_count=0,
                staged_count=0,
                unstaged_count=0,
                untracked_count=0,
                stash_count=0,
                worktree_count=0,
                pr_info=None,
                last_modified=datetime.now(),
                status=RepoStatus.WARNING,
                has_remote=False,
            )

    async def get_worktree_count(self, repo_path: Path) -> int:
        """Get count of jj workspaces (always 0 for now as multi-workspace is rare)"""
        cache_key = f"{repo_path}:worktree_count"
        if cached := commit_cache.get(cache_key):
            return cached

        output = await self._run_jj_async(repo_path, "workspace", "list")
        count = len([line for line in output.splitlines() if line.strip() and not line.startswith("default@")])
        commit_cache.set(cache_key, count)
        return count

    async def get_worktree_list(self, repo_path: Path) -> list[WorktreeInfo]:
        """Get list of jj workspaces"""
        cache_key = f"{repo_path}:worktrees"
        if cached := commit_cache.get(cache_key):
            return cached

        output = await self._run_jj_async(repo_path, "workspace", "list")

        workspaces = []
        for line in output.splitlines():
            if not line.strip():
                continue

            match = re.match(r"(\S+)@(\S+):\s+(\S+)", line)
            if not match:
                continue

            workspace_name, change_id, path_str = match.groups()
            is_main = workspace_name == "default"

            workspaces.append(
                WorktreeInfo(
                    path=Path(path_str),
                    branch=workspace_name if workspace_name != "default" else None,
                    commit=change_id,
                    is_main=is_main,
                    is_detached=False,
                )
            )

        result = workspaces[1:] if len(workspaces) > 1 else []
        commit_cache.set(cache_key, result)
        return result

    async def get_stash_count(self, repo_path: Path) -> int:
        """Get stash count (always 0 for jj - no stash concept)"""
        return 0

    async def get_stash_list(self, repo_path: Path) -> list[dict]:
        """Get stash list (always empty for jj)"""
        return []

    async def get_stash_detail(self, repo_path: Path, stash_name: str) -> StashDetail:
        """Get stash detail (not applicable for jj)"""
        raise NotImplementedError("JJ does not have stash concept")

    async def get_commits_ahead(self, repo_path: Path, bookmark: str) -> list[CommitInfo]:
        """Get commits ahead of tracking bookmark"""
        cache_key = f"{repo_path}:{bookmark}:ahead"
        if cached := commit_cache.get(cache_key):
            return cached

        try:
            output = await self._run_jj_async(
                repo_path,
                "log",
                "-r",
                f"{bookmark}@origin..",
                "-T",
                'change_id.short() ++ "|" ++ description.first_line() ++ "|" ++ author.name() ++ "|" ++ committer_date',
            )
            result = self._parse_commit_list(output)
            commit_cache.set(cache_key, result)
            return result
        except Exception:
            return []

    async def get_commits_behind(self, repo_path: Path, bookmark: str) -> list[CommitInfo]:
        """Get commits behind tracking bookmark"""
        cache_key = f"{repo_path}:{bookmark}:behind"
        if cached := commit_cache.get(cache_key):
            return cached

        try:
            output = await self._run_jj_async(
                repo_path,
                "log",
                "-r",
                f"..{bookmark}@origin",
                "-T",
                'change_id.short() ++ "|" ++ description.first_line() ++ "|" ++ author.name() ++ "|" ++ committer_date',
            )
            result = self._parse_commit_list(output)
            commit_cache.set(cache_key, result)
            return result
        except Exception:
            return []

    def _parse_commit_list(self, output: str) -> list[CommitInfo]:
        """Parse commit list from jj log output"""
        commits = []
        for line in output.splitlines():
            if not line.strip():
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

    async def get_upstream_repo(self, repo_path: Path) -> str | None:
        """Get upstream repo identifier"""
        try:
            output = await self._run_jj_async(repo_path, "git", "remote", "list")
            for line in output.splitlines():
                if line.startswith("origin"):
                    url = line.split(None, 1)[1] if len(line.split()) > 1 else ""
                    if m := re.search(r"github\.com[:/](.+?)(?:\.git)?$", url):
                        return m.group(1)
        except Exception:
            pass
        return None

    async def get_commit_sha(self, repo_path: Path, ref: str) -> str | None:
        """Get commit SHA for a given ref (bookmark, change ID, etc.)"""
        try:
            output = await self._run_jj_async(repo_path, "log", "-r", ref, "-T", "commit_id", "--no-graph")
            return output.strip()
        except Exception:
            return None

    async def fetch_all(self, repo_path: Path) -> tuple[bool, str]:
        """Fetch from all remotes"""
        try:
            output = await self._run_jj_async(repo_path, "git", "fetch", "--all-remotes")
            return True, f"Fetched successfully: {output[:100]}"
        except Exception as err:
            return False, f"Fetch failed: {err!s}"

    async def prune_remote(self, repo_path: Path) -> tuple[bool, str]:
        """Prune remote (no-op for jj, implicit in fetch)"""
        return True, "JJ doesn't require explicit pruning (handled by fetch)"

    async def cleanup_merged_branches(self, repo_path: Path) -> tuple[bool, str]:
        """Cleanup merged bookmarks"""
        try:
            output = await self._run_jj_async(
                repo_path,
                "bookmark",
                "list",
            )

            deleted = []
            for line in output.splitlines():
                if not line.strip():
                    continue
                parts = line.split(":")
                if len(parts) < 1:
                    continue
                bookmark = parts[0].strip()

                if bookmark in ("main", "master", "trunk"):
                    continue

                try:
                    is_merged = await self._run_jj_async(
                        repo_path,
                        "log",
                        "-r",
                        f"{bookmark}@origin..main@origin",
                        "-T",
                        "commit_id",
                    )
                    if not is_merged.strip():
                        await self._run_jj_async(repo_path, "bookmark", "delete", bookmark)
                        deleted.append(bookmark)
                except Exception:
                    continue

            if deleted:
                return True, f"Deleted {len(deleted)} merged bookmarks: {', '.join(deleted)}"
            return True, "No merged bookmarks to delete"
        except Exception as err:
            return False, f"Cleanup failed: {err!s}"
