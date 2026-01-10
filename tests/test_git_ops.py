from pathlib import Path
from unittest.mock import patch

from multi_repo_view.git_ops import (
    _get_ahead_behind,
    _get_uncommitted_count,
    _parse_ahead_behind,
    get_branch_list,
    get_current_branch,
    get_repo_summary,
    get_status_files,
)


class TestGetCurrentBranch:
    def test_returns_branch_name(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value="main"):
            result = get_current_branch(Path("/repo"))
            assert result == "main"

    def test_returns_head_when_empty(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value=""):
            result = get_current_branch(Path("/repo"))
            assert result == "HEAD"


class TestUncommittedCount:
    def test_no_changes_returns_zero(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value=""):
            result = _get_uncommitted_count(Path("/repo"))
            assert result == 0

    def test_counts_changes(self) -> None:
        with patch(
            "multi_repo_view.git_ops._run_git", return_value=" M file.py\n?? new.py"
        ):
            result = _get_uncommitted_count(Path("/repo"))
            assert result == 2


class TestParseAheadBehind:
    def test_no_tracking_returns_zeros(self) -> None:
        ahead, behind = _parse_ahead_behind("## main")
        assert ahead == 0
        assert behind == 0

    def test_parses_ahead(self) -> None:
        ahead, behind = _parse_ahead_behind("## main...origin/main [ahead 3]")
        assert ahead == 3
        assert behind == 0

    def test_parses_behind(self) -> None:
        ahead, behind = _parse_ahead_behind("## main...origin/main [behind 2]")
        assert ahead == 0
        assert behind == 2

    def test_parses_ahead_and_behind(self) -> None:
        ahead, behind = _parse_ahead_behind(
            "## main...origin/main [ahead 3, behind 2]"
        )
        assert ahead == 3
        assert behind == 2


class TestGetAheadBehind:
    def test_returns_counts(self) -> None:
        with patch(
            "multi_repo_view.git_ops._run_git",
            return_value="## main...origin/main [ahead 2]",
        ):
            ahead, behind = _get_ahead_behind(Path("/repo"))
            assert ahead == 2
            assert behind == 0


class TestGetBranchList:
    def test_empty_output_returns_empty_list(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value=""):
            result = get_branch_list(Path("/repo"))
            assert result == []

    def test_parses_branches_with_tracking(self) -> None:
        output = "main|origin/main|[ahead 2, behind 1]\nfeature|origin/feature|"
        with (
            patch("multi_repo_view.git_ops._run_git", return_value=output),
            patch("multi_repo_view.git_ops.get_current_branch", return_value="main"),
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

    def test_parses_local_only_branch(self) -> None:
        output = "local-branch||"
        with (
            patch("multi_repo_view.git_ops._run_git", return_value=output),
            patch("multi_repo_view.git_ops.get_current_branch", return_value="main"),
        ):
            result = get_branch_list(Path("/repo"))
            assert len(result) == 1
            assert result[0].tracking is None


class TestGetStatusFiles:
    def test_empty_status_returns_empty_lists(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value=""):
            untracked, modified, staged = get_status_files(Path("/repo"))
            assert untracked == []
            assert modified == []
            assert staged == []

    def test_parses_untracked_files(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value="?? new_file.py"):
            untracked, modified, staged = get_status_files(Path("/repo"))
            assert untracked == ["new_file.py"]
            assert modified == []
            assert staged == []

    def test_parses_modified_files(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value=" M changed.py"):
            untracked, modified, staged = get_status_files(Path("/repo"))
            assert untracked == []
            assert modified == ["changed.py"]
            assert staged == []

    def test_parses_staged_files(self) -> None:
        with patch("multi_repo_view.git_ops._run_git", return_value="A  added.py"):
            untracked, modified, staged = get_status_files(Path("/repo"))
            assert untracked == []
            assert modified == []
            assert staged == ["added.py"]

    def test_parses_mixed_status(self) -> None:
        output = "?? new.py\n M changed.py\nA  added.py\nMM both.py"
        with patch("multi_repo_view.git_ops._run_git", return_value=output):
            untracked, modified, staged = get_status_files(Path("/repo"))
            assert untracked == ["new.py"]
            assert "changed.py" in modified
            assert "both.py" in modified
            assert "added.py" in staged
            assert "both.py" in staged


class TestGetRepoSummary:
    def test_creates_summary_with_all_fields(self) -> None:
        with (
            patch("multi_repo_view.git_ops.get_current_branch", return_value="develop"),
            patch("multi_repo_view.git_ops._get_ahead_behind", return_value=(2, 1)),
            patch("multi_repo_view.git_ops._get_uncommitted_count", return_value=3),
        ):
            result = get_repo_summary(Path("/path/to/my-repo"))
            assert result.path == Path("/path/to/my-repo")
            assert result.name == "my-repo"
            assert result.current_branch == "develop"
            assert result.ahead_count == 2
            assert result.behind_count == 1
            assert result.uncommitted_count == 3
            assert result.is_dirty is True

    def test_clean_repo_is_not_dirty(self) -> None:
        with (
            patch("multi_repo_view.git_ops.get_current_branch", return_value="main"),
            patch("multi_repo_view.git_ops._get_ahead_behind", return_value=(0, 0)),
            patch("multi_repo_view.git_ops._get_uncommitted_count", return_value=0),
        ):
            result = get_repo_summary(Path("/path/to/clean-repo"))
            assert result.is_dirty is False
