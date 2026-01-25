from pathlib import Path

from repo_dashboard import git_ops
from repo_dashboard.models import BranchInfo, CommitInfo, RepoSummary, StashDetail, WorktreeInfo
from repo_dashboard.vcs_protocol import VCSType


class GitOperations:
    """Git implementation of VCS operations"""

    vcs_type: VCSType = "git"

    def get_repo_summary(self, repo_path: Path) -> RepoSummary:
        """Get repository summary with status, branches, counts"""
        return git_ops.get_repo_summary(repo_path)

    async def get_repo_summary_async(self, repo_path: Path) -> RepoSummary:
        """Async version of get_repo_summary"""
        return await git_ops.get_repo_summary_async(repo_path)

    def get_current_branch(self, repo_path: Path) -> str:
        """Get current branch name"""
        return git_ops.get_current_branch(repo_path)

    async def get_current_branch_async(self, repo_path: Path) -> str:
        """Async version of get_current_branch"""
        return await git_ops.get_current_branch_async(repo_path)

    async def get_branch_list_async(self, repo_path: Path) -> list[BranchInfo]:
        """Get list of branches with tracking info"""
        return await git_ops.get_branch_list_async(repo_path)

    async def get_worktree_list(self, repo_path: Path) -> list[WorktreeInfo]:
        """Get list of git worktrees"""
        return await git_ops.get_worktree_list(repo_path)

    async def get_worktree_count(self, repo_path: Path) -> int:
        """Get count of worktrees (excluding main)"""
        return await git_ops.get_worktree_count(repo_path)

    async def get_stash_list(self, repo_path: Path) -> list[dict]:
        """Get list of stashes"""
        return await git_ops.get_stash_list(repo_path)

    async def get_stash_count(self, repo_path: Path) -> int:
        """Get count of stashes"""
        return await git_ops.get_stash_count(repo_path)

    async def get_stash_detail(self, repo_path: Path, stash_name: str) -> StashDetail:
        """Get detailed stash information"""
        return await git_ops.get_stash_detail(repo_path, stash_name)

    async def get_commits_ahead(self, repo_path: Path, branch: str) -> list[CommitInfo]:
        """Get commits ahead of tracking branch"""
        return await git_ops.get_commits_ahead(repo_path, branch)

    async def get_commits_behind(self, repo_path: Path, branch: str) -> list[CommitInfo]:
        """Get commits behind tracking branch"""
        return await git_ops.get_commits_behind(repo_path, branch)

    async def get_status_files_async(
        self, repo_path: Path
    ) -> tuple[list[str], list[str], list[str]]:
        """Get untracked, modified, and staged files"""
        return await git_ops.get_status_files_async(repo_path)

    async def get_upstream_repo(self, repo_path: Path) -> str | None:
        """Get upstream repo identifier (e.g., 'owner/repo')"""
        return await git_ops.get_upstream_repo(repo_path)

    async def get_commit_sha(self, repo_path: Path, ref: str) -> str | None:
        """Get commit SHA for a given ref (branch, tag, etc.)"""
        import asyncio

        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_path),
                "rev-parse",
                ref,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                return stdout.decode().strip()
            return None
        except Exception:
            return None

    async def fetch_all(self, repo_path: Path) -> tuple[bool, str]:
        """Fetch from all remotes with prune"""
        import asyncio
        import subprocess

        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_path),
                "fetch",
                "--all",
                "--prune",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = (stdout.decode() + stderr.decode()).strip()

            if proc.returncode == 0:
                return (True, output or "Fetched successfully")
            return (False, output or "Fetch failed")
        except Exception as err:
            return (False, f"Error: {err}")

    async def prune_remote(self, repo_path: Path) -> tuple[bool, str]:
        """Prune stale remote branches"""
        import asyncio
        import subprocess

        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_path),
                "remote",
                "prune",
                "origin",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = (stdout.decode() + stderr.decode()).strip()

            if proc.returncode == 0:
                return (True, output or "Pruned successfully")
            return (False, output or "Prune failed")
        except Exception as err:
            return (False, f"Error: {err}")

    async def cleanup_merged_branches(self, repo_path: Path) -> tuple[bool, str]:
        """Delete local branches merged into main/master"""
        import asyncio
        import subprocess

        try:
            main_branch = "main"
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_path),
                "rev-parse",
                "--verify",
                "main",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                main_branch = "master"

            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_path),
                "branch",
                "--merged",
                main_branch,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            branches = [
                b.strip().lstrip("* ")
                for b in stdout.decode().splitlines()
                if b.strip() and not b.strip().lstrip("* ") in (main_branch, "master", "HEAD")
            ]

            if not branches:
                return (True, "No merged branches to clean up")

            deleted = []
            failed = []
            for branch in branches:
                proc = await asyncio.create_subprocess_exec(
                    "git",
                    "-C",
                    str(repo_path),
                    "branch",
                    "-d",
                    branch,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    deleted.append(branch)
                else:
                    failed.append(branch)

            if deleted and not failed:
                return (True, f"Deleted {len(deleted)} branches: {', '.join(deleted)}")
            if deleted and failed:
                return (
                    True,
                    f"Deleted {len(deleted)}, failed {len(failed)}: {', '.join(deleted)}",
                )
            return (False, f"Failed to delete branches: {', '.join(failed)}")
        except Exception as err:
            return (False, f"Error: {err}")
