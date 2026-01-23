import os
from pathlib import Path

from repo_dashboard.vcs_git import GitOperations
from repo_dashboard.vcs_jj import JJOperations
from repo_dashboard.vcs_protocol import VCSOperations, VCSType


def detect_vcs_type(repo_path: Path) -> VCSType | None:
    """Detect VCS type by directory presence

    Prefers jj if both .git and .jj exist (colocated repos)
    """
    if (repo_path / ".jj").is_dir():
        return "jj"
    if (repo_path / ".git").is_dir():
        return "git"
    return None


def get_vcs_operations(repo_path: Path) -> VCSOperations:
    """Factory function to get appropriate VCS operations

    Raises ValueError if no VCS repository found
    """
    vcs_type = detect_vcs_type(repo_path)

    if vcs_type == "jj":
        return JJOperations()
    if vcs_type == "git":
        return GitOperations()

    raise ValueError(f"No VCS repository found at {repo_path}")


def get_github_env(vcs_ops: VCSOperations, repo_path: Path) -> dict[str, str]:
    """Get environment variables for gh CLI

    For non-colocated jj repos, sets GIT_DIR to point to .jj/repo/store/git
    For git repos, returns unmodified environment
    """
    env = os.environ.copy()

    if vcs_ops.vcs_type == "jj":
        if hasattr(vcs_ops, "_get_git_dir"):
            env["GIT_DIR"] = vcs_ops._get_git_dir(repo_path)

    return env
