from datetime import datetime
from pathlib import Path

from repo_dashboard.models import RepoStatus, RepoSummary


def test_repo_status_enum_has_all_statuses() -> None:
    """Test that all expected statuses exist in enum"""
    assert RepoStatus.OK == "ok"
    assert RepoStatus.WARNING == "warning"
    assert RepoStatus.NO_GIT == "no_git"
    assert RepoStatus.NO_JJ == "no_jj"
    assert RepoStatus.NO_GH == "no_gh"
    assert RepoStatus.NO_UPSTREAM == "no_upstream"
    assert RepoStatus.DETACHED_HEAD == "detached_head"
    assert RepoStatus.LOADING == "loading"


def test_warning_message_ok_returns_none() -> None:
    """Test that OK status returns no warning message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
        current_branch="main",
        ahead_count=0,
        behind_count=0,
        staged_count=0,
        unstaged_count=0,
        untracked_count=0,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.OK,
    )
    assert summary.warning_message is None


def test_warning_message_loading_returns_none() -> None:
    """Test that LOADING status returns no warning message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
        current_branch="...",
        ahead_count=0,
        behind_count=0,
        staged_count=0,
        unstaged_count=0,
        untracked_count=0,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.LOADING,
    )
    assert summary.warning_message is None


def test_warning_message_no_git() -> None:
    """Test NO_GIT status message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
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
        status=RepoStatus.NO_GIT,
    )
    assert summary.warning_message == "Git not installed"


def test_warning_message_no_jj() -> None:
    """Test NO_JJ status message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
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
    )
    assert summary.warning_message == "Jujutsu (jj) not installed"


def test_warning_message_no_gh() -> None:
    """Test NO_GH status message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
        current_branch="main",
        ahead_count=0,
        behind_count=0,
        staged_count=0,
        unstaged_count=0,
        untracked_count=0,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.NO_GH,
    )
    assert summary.warning_message == "GitHub CLI (gh) not installed"


def test_warning_message_no_upstream() -> None:
    """Test NO_UPSTREAM status message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
        current_branch="main",
        ahead_count=0,
        behind_count=0,
        staged_count=0,
        unstaged_count=0,
        untracked_count=0,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.NO_UPSTREAM,
    )
    assert summary.warning_message == "No upstream configured"


def test_warning_message_detached_head() -> None:
    """Test DETACHED_HEAD status message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
        current_branch="HEAD",
        ahead_count=0,
        behind_count=0,
        staged_count=0,
        unstaged_count=0,
        untracked_count=0,
        stash_count=0,
        worktree_count=0,
        pr_info=None,
        last_modified=datetime.now(),
        status=RepoStatus.DETACHED_HEAD,
    )
    assert summary.warning_message == "Detached HEAD state"


def test_warning_message_generic_warning() -> None:
    """Test generic WARNING status message"""
    summary = RepoSummary(
        path=Path("/repo"),
        name="repo",
        vcs_type="git",
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
    )
    assert summary.warning_message == "Unknown issue"
