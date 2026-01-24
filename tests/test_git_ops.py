import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from repo_dashboard.git_ops import (
    _get_ahead_behind,
    _get_uncommitted_count,
    _is_detached_head,
    _parse_ahead_behind,
    get_branch_list,
    get_current_branch,
    get_repo_summary,
    get_status_files,
)
from repo_dashboard.models import RepoStatus


def test_get_current_branch_returns_branch_name() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value="main"):
        result = get_current_branch(Path("/repo"))
        assert result == "main"


def test_get_current_branch_returns_head_when_empty() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value=""):
        result = get_current_branch(Path("/repo"))
        assert result == "HEAD"


def test_uncommitted_count_no_changes_returns_zero() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value=""):
        result = _get_uncommitted_count(Path("/repo"))
        assert result == 0


def test_uncommitted_count_counts_changes() -> None:
    with patch(
        "repo_dashboard.git_ops._run_git", return_value=" M file.py\n?? new.py"
    ):
        result = _get_uncommitted_count(Path("/repo"))
        assert result == 2


def test_parse_ahead_behind_no_tracking_returns_zeros() -> None:
    ahead, behind = _parse_ahead_behind("## main")
    assert ahead == 0
    assert behind == 0


def test_parse_ahead_behind_parses_ahead() -> None:
    ahead, behind = _parse_ahead_behind("## main...origin/main [ahead 3]")
    assert ahead == 3
    assert behind == 0


def test_parse_ahead_behind_parses_behind() -> None:
    ahead, behind = _parse_ahead_behind("## main...origin/main [behind 2]")
    assert ahead == 0
    assert behind == 2


def test_parse_ahead_behind_parses_ahead_and_behind() -> None:
    ahead, behind = _parse_ahead_behind(
        "## main...origin/main [ahead 3, behind 2]"
    )
    assert ahead == 3
    assert behind == 2


def test_get_ahead_behind_returns_counts() -> None:
    with patch(
        "repo_dashboard.git_ops._run_git",
        return_value="## main...origin/main [ahead 2]",
    ):
        ahead, behind = _get_ahead_behind(Path("/repo"))
        assert ahead == 2
        assert behind == 0


def test_get_branch_list_empty_output_returns_empty_list() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value=""):
        result = get_branch_list(Path("/repo"))
        assert result == []


def test_get_branch_list_parses_branches_with_tracking() -> None:
    output = "main|origin/main|[ahead 2, behind 1]\nfeature|origin/feature|"
    with (
        patch("repo_dashboard.git_ops._run_git", return_value=output),
        patch("repo_dashboard.git_ops.get_current_branch", return_value="main"),
    ):
        result = get_branch_list(Path("/repo"))
        assert len(result) == 2
        assert result[0].name == "main"
        assert result[0].is_current is True
        assert result[0].ahead == 2
        assert result[0].behind == 1
        assert result[0].tracking == "origin/main"
        assert result[1].name == "feature"
        assert result[1].is_current is False


def test_get_branch_list_parses_local_only_branch() -> None:
    output = "local-branch||"
    with (
        patch("repo_dashboard.git_ops._run_git", return_value=output),
        patch("repo_dashboard.git_ops.get_current_branch", return_value="main"),
    ):
        result = get_branch_list(Path("/repo"))
        assert len(result) == 1
        assert result[0].tracking is None


def test_get_status_files_empty_status_returns_empty_lists() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value=""):
        untracked, modified, staged = get_status_files(Path("/repo"))
        assert untracked == []
        assert modified == []
        assert staged == []


def test_get_status_files_parses_untracked_files() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value="?? new_file.py"):
        untracked, modified, staged = get_status_files(Path("/repo"))
        assert untracked == ["new_file.py"]
        assert modified == []
        assert staged == []


def test_get_status_files_parses_modified_files() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value=" M changed.py"):
        untracked, modified, staged = get_status_files(Path("/repo"))
        assert untracked == []
        assert modified == ["changed.py"]
        assert staged == []


def test_get_status_files_parses_staged_files() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value="A  added.py"):
        untracked, modified, staged = get_status_files(Path("/repo"))
        assert untracked == []
        assert modified == []
        assert staged == ["added.py"]


def test_get_status_files_parses_mixed_status() -> None:
    output = "?? new.py\n M changed.py\nA  added.py\nMM both.py"
    with patch("repo_dashboard.git_ops._run_git", return_value=output):
        untracked, modified, staged = get_status_files(Path("/repo"))
        assert untracked == ["new.py"]
        assert "changed.py" in modified
        assert "both.py" in modified
        assert "added.py" in staged
        assert "both.py" in staged


def test_get_repo_summary_creates_summary_with_all_fields() -> None:
    with (
        patch("repo_dashboard.git_ops.get_current_branch", return_value="develop"),
        patch("repo_dashboard.git_ops._get_ahead_behind", return_value=(2, 1)),
        patch("repo_dashboard.git_ops._get_status_counts", return_value=(1, 2, 0)),
    ):
        result = get_repo_summary(Path("/path/to/my-repo"))
        assert result.path == Path("/path/to/my-repo")
        assert result.name == "my-repo"
        assert result.current_branch == "develop"
        assert result.ahead_count == 2
        assert result.behind_count == 1
        assert result.staged_count == 1
        assert result.unstaged_count == 2
        assert result.untracked_count == 0
        assert result.uncommitted_count == 3
        assert result.is_dirty is True


def test_get_repo_summary_clean_repo_is_not_dirty() -> None:
    with (
        patch("repo_dashboard.git_ops.get_current_branch", return_value="main"),
        patch("repo_dashboard.git_ops._get_ahead_behind", return_value=(0, 0)),
        patch("repo_dashboard.git_ops._get_status_counts", return_value=(0, 0, 0)),
    ):
        result = get_repo_summary(Path("/path/to/clean-repo"))
        assert result.is_dirty is False


def test_is_detached_head_returns_true_when_detached() -> None:
    with patch("repo_dashboard.git_ops._run_git", side_effect=Exception("not a branch")):
        result = _is_detached_head(Path("/repo"))
        assert result is True


def test_is_detached_head_returns_false_when_on_branch() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value="refs/heads/main"):
        result = _is_detached_head(Path("/repo"))
        assert result is False


def test_is_detached_head_returns_true_when_empty_result() -> None:
    with patch("repo_dashboard.git_ops._run_git", return_value=""):
        result = _is_detached_head(Path("/repo"))
        assert result is True
