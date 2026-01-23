import time
from dataclasses import dataclass
from pathlib import Path

from repo_dashboard.models import RepoSummary
from repo_dashboard.vcs_factory import get_vcs_operations
from repo_dashboard.vcs_protocol import VCSOperations


@dataclass(frozen=True)
class BatchTaskResult:
    """Result of a batch task operation on a single repository"""

    repo_path: Path
    repo_name: str
    success: bool
    message: str
    duration_ms: int


class BatchTaskRunner:
    """Execute tasks across multiple repositories with progress tracking"""

    def __init__(self, repos: list[RepoSummary]):
        self.repos = repos

    async def run_task(
        self,
        task_fn: callable,
    ) -> list[BatchTaskResult]:
        """Run task across all repos sequentially

        Args:
            task_fn: Async function taking (vcs_ops, repo_path) -> (bool, str)

        Returns:
            List of BatchTaskResult for each repository
        """
        results = []
        for repo in self.repos:
            vcs_ops = get_vcs_operations(repo.path)
            start = time.time()

            try:
                success, message = await task_fn(vcs_ops, repo.path)
            except Exception as err:
                success, message = False, f"Error: {err}"

            duration = int((time.time() - start) * 1000)

            results.append(
                BatchTaskResult(
                    repo_path=repo.path,
                    repo_name=repo.name,
                    success=success,
                    message=message,
                    duration_ms=duration,
                )
            )

        return results


async def task_fetch_all(vcs_ops: VCSOperations, repo_path: Path) -> tuple[bool, str]:
    """Fetch from all remotes"""
    return await vcs_ops.fetch_all(repo_path)


async def task_prune_remote(
    vcs_ops: VCSOperations, repo_path: Path
) -> tuple[bool, str]:
    """Prune stale remote branches"""
    return await vcs_ops.prune_remote(repo_path)


async def task_cleanup_merged(
    vcs_ops: VCSOperations, repo_path: Path
) -> tuple[bool, str]:
    """Delete local branches merged into main/master"""
    return await vcs_ops.cleanup_merged_branches(repo_path)
