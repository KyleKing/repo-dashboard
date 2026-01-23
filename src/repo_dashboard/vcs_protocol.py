from pathlib import Path
from typing import Literal, Protocol

from repo_dashboard.models import BranchInfo, CommitInfo, RepoSummary, StashDetail, WorktreeInfo

VCSType = Literal["git", "jj"]


class VCSOperations(Protocol):
    """Protocol for VCS operations - both git and jj must implement this interface"""

    vcs_type: VCSType

    # Read operations (existing functionality)
    def get_repo_summary(self, repo_path: Path) -> RepoSummary:
        """Get repository summary with status, branches, counts"""
        ...

    async def get_repo_summary_async(self, repo_path: Path) -> RepoSummary:
        """Async version of get_repo_summary"""
        ...

    def get_current_branch(self, repo_path: Path) -> str:
        """Get current branch/bookmark name"""
        ...

    async def get_current_branch_async(self, repo_path: Path) -> str:
        """Async version of get_current_branch"""
        ...

    async def get_branch_list_async(self, repo_path: Path) -> list[BranchInfo]:
        """Get list of branches/bookmarks with tracking info"""
        ...

    async def get_worktree_list(self, repo_path: Path) -> list[WorktreeInfo]:
        """Get list of worktrees (git) or workspaces (jj)"""
        ...

    async def get_worktree_count(self, repo_path: Path) -> int:
        """Get count of worktrees/workspaces (excluding main)"""
        ...

    async def get_stash_list(self, repo_path: Path) -> list[dict]:
        """Get list of stashes (git only, returns empty for jj)"""
        ...

    async def get_stash_count(self, repo_path: Path) -> int:
        """Get count of stashes"""
        ...

    async def get_stash_detail(self, repo_path: Path, stash_name: str) -> StashDetail:
        """Get detailed stash information"""
        ...

    async def get_commits_ahead(self, repo_path: Path, branch: str) -> list[CommitInfo]:
        """Get commits ahead of tracking branch"""
        ...

    async def get_commits_behind(self, repo_path: Path, branch: str) -> list[CommitInfo]:
        """Get commits behind tracking branch"""
        ...

    async def get_status_files_async(
        self, repo_path: Path
    ) -> tuple[list[str], list[str], list[str]]:
        """Get untracked, modified, and staged files"""
        ...

    async def get_upstream_repo(self, repo_path: Path) -> str | None:
        """Get upstream repo identifier (e.g., 'owner/repo')"""
        ...

    # Write operations (new - batch maintenance tasks)
    async def fetch_all(self, repo_path: Path) -> tuple[bool, str]:
        """Fetch from all remotes. Returns (success, message)"""
        ...

    async def prune_remote(self, repo_path: Path) -> tuple[bool, str]:
        """Prune stale remote branches. Returns (success, message)"""
        ...

    async def cleanup_merged_branches(self, repo_path: Path) -> tuple[bool, str]:
        """Delete local branches merged into main. Returns (success, message)"""
        ...
