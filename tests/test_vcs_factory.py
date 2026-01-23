from pathlib import Path

import pytest

from repo_dashboard.vcs_factory import detect_vcs_type, get_vcs_operations
from repo_dashboard.vcs_git import GitOperations
from repo_dashboard.vcs_jj import JJOperations


def test_detect_git_repo(tmp_path: Path) -> None:
    """Test detection of git repository"""
    repo = tmp_path / "git-repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    assert detect_vcs_type(repo) == "git"


def test_detect_jj_repo(tmp_path: Path) -> None:
    """Test detection of jj repository"""
    repo = tmp_path / "jj-repo"
    repo.mkdir()
    (repo / ".jj").mkdir()

    assert detect_vcs_type(repo) == "jj"


def test_detect_colocated_prefers_jj(tmp_path: Path) -> None:
    """Test that colocated repos (both .git and .jj) prefer jj"""
    repo = tmp_path / "colocated"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".jj").mkdir()

    assert detect_vcs_type(repo) == "jj"


def test_detect_no_vcs(tmp_path: Path) -> None:
    """Test detection returns None for non-VCS directory"""
    repo = tmp_path / "not-a-repo"
    repo.mkdir()

    assert detect_vcs_type(repo) is None


def test_get_vcs_operations_git(tmp_path: Path) -> None:
    """Test factory returns GitOperations for git repos"""
    repo = tmp_path / "git-repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    ops = get_vcs_operations(repo)
    assert isinstance(ops, GitOperations)
    assert ops.vcs_type == "git"


def test_get_vcs_operations_jj(tmp_path: Path) -> None:
    """Test factory returns JJOperations for jj repos"""
    repo = tmp_path / "jj-repo"
    repo.mkdir()
    (repo / ".jj").mkdir()

    ops = get_vcs_operations(repo)
    assert isinstance(ops, JJOperations)
    assert ops.vcs_type == "jj"


def test_get_vcs_operations_no_vcs(tmp_path: Path) -> None:
    """Test factory raises ValueError for non-VCS directory"""
    repo = tmp_path / "not-a-repo"
    repo.mkdir()

    with pytest.raises(ValueError, match="No VCS repository found"):
        get_vcs_operations(repo)


def test_get_vcs_operations_colocated(tmp_path: Path) -> None:
    """Test factory returns JJOperations for colocated repos"""
    repo = tmp_path / "colocated"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".jj").mkdir()

    ops = get_vcs_operations(repo)
    assert isinstance(ops, JJOperations)
    assert ops.vcs_type == "jj"
