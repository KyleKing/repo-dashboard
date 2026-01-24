from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from repo_dashboard.vcs_jj import JJOperations


@pytest.fixture
def jj_ops() -> JJOperations:
    """Create JJ operations instance"""
    return JJOperations()


@pytest.fixture
def mock_jj_repo(tmp_path: Path) -> Path:
    """Create mock jj repository"""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    (repo / ".jj").mkdir()
    return repo


@pytest.fixture
def mock_colocated_jj_repo(tmp_path: Path) -> Path:
    """Create mock colocated jj repository (has both .jj and .git)"""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    (repo / ".jj").mkdir()
    (repo / ".git").mkdir()
    return repo


def test_is_colocated_true(jj_ops: JJOperations, mock_colocated_jj_repo: Path) -> None:
    """Test colocated detection for repos with both .git and .jj"""
    assert jj_ops._is_colocated(mock_colocated_jj_repo) is True


def test_is_colocated_false(jj_ops: JJOperations, mock_jj_repo: Path) -> None:
    """Test colocated detection for repos with only .jj"""
    assert jj_ops._is_colocated(mock_jj_repo) is False


def test_get_git_dir_colocated(jj_ops: JJOperations, mock_colocated_jj_repo: Path) -> None:
    """Test GIT_DIR for colocated repos points to .git"""
    git_dir = jj_ops._get_git_dir(mock_colocated_jj_repo)
    assert git_dir == str(mock_colocated_jj_repo / ".git")


def test_get_git_dir_noncolocated(jj_ops: JJOperations, mock_jj_repo: Path) -> None:
    """Test GIT_DIR for non-colocated repos points to .jj/repo/store/git"""
    git_dir = jj_ops._get_git_dir(mock_jj_repo)
    assert git_dir == str(mock_jj_repo / ".jj" / "repo" / "store" / "git")


def test_get_current_branch(jj_ops: JJOperations, mock_jj_repo: Path) -> None:
    """Test getting current bookmark"""
    with patch.object(jj_ops, "_run_jj", return_value="main"):
        branch = jj_ops.get_current_branch(mock_jj_repo)
        assert branch == "main"


def test_get_current_branch_no_bookmark(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test getting current bookmark when none exists"""
    with patch.object(jj_ops, "_run_jj", return_value=""):
        branch = jj_ops.get_current_branch(mock_jj_repo)
        assert branch == "@"


@pytest.mark.asyncio
async def test_get_current_branch_async(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test getting current bookmark asynchronously"""
    with patch.object(jj_ops, "_run_jj_async", return_value=AsyncMock(return_value="feature")):
        jj_ops._run_jj_async = AsyncMock(return_value="feature")
        branch = await jj_ops.get_current_branch_async(mock_jj_repo)
        assert branch == "feature"


@pytest.mark.asyncio
async def test_get_repo_summary_async(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test getting repository summary"""
    with (
        patch.object(jj_ops, "get_current_branch_async", return_value=AsyncMock(return_value="main")),
        patch.object(jj_ops, "_get_ahead_behind_async", return_value=AsyncMock(return_value=(2, 1))),
        patch.object(jj_ops, "_get_status_counts_async", return_value=AsyncMock(return_value=(0, 3, 0))),
        patch.object(jj_ops, "get_worktree_count", return_value=AsyncMock(return_value=0)),
        patch.object(jj_ops, "_run_jj_async", return_value=AsyncMock(return_value="2024-01-01T00:00:00Z")),
        patch.object(jj_ops, "_check_tracking_exists", return_value=AsyncMock(return_value=True)),
    ):
        jj_ops.get_current_branch_async = AsyncMock(return_value="main")
        jj_ops._get_ahead_behind_async = AsyncMock(return_value=(2, 1))
        jj_ops._get_status_counts_async = AsyncMock(return_value=(0, 3, 0))
        jj_ops.get_worktree_count = AsyncMock(return_value=0)
        jj_ops._run_jj_async = AsyncMock(return_value="2024-01-01T00:00:00Z")
        jj_ops._check_tracking_exists = AsyncMock(return_value=True)

        summary = await jj_ops.get_repo_summary_async(mock_jj_repo)

        assert summary.vcs_type == "jj"
        assert summary.current_branch == "main"
        assert summary.ahead_count == 2
        assert summary.behind_count == 1
        assert summary.staged_count == 0
        assert summary.unstaged_count == 3
        assert summary.untracked_count == 0
        assert summary.uncommitted_count == 3
        assert summary.has_remote is True
        assert summary.jj_is_colocated is False


@pytest.mark.asyncio
async def test_get_stash_count_always_zero(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test that jj repos always have 0 stashes"""
    count = await jj_ops.get_stash_count(mock_jj_repo)
    assert count == 0


@pytest.mark.asyncio
async def test_get_stash_list_always_empty(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test that jj repos always have empty stash list"""
    stashes = await jj_ops.get_stash_list(mock_jj_repo)
    assert stashes == []


@pytest.mark.asyncio
async def test_get_stash_detail_not_implemented(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test that getting stash detail raises NotImplementedError"""
    with pytest.raises(NotImplementedError, match="JJ does not have stash concept"):
        await jj_ops.get_stash_detail(mock_jj_repo, "stash@{0}")


@pytest.mark.asyncio
async def test_fetch_all_success(jj_ops: JJOperations, mock_jj_repo: Path) -> None:
    """Test successful fetch"""
    jj_ops._run_jj_async = AsyncMock(return_value="Fetched from origin")
    success, message = await jj_ops.fetch_all(mock_jj_repo)
    assert success is True
    assert "Fetched successfully" in message


@pytest.mark.asyncio
async def test_fetch_all_failure(jj_ops: JJOperations, mock_jj_repo: Path) -> None:
    """Test fetch failure"""
    jj_ops._run_jj_async = AsyncMock(side_effect=Exception("Network error"))
    success, message = await jj_ops.fetch_all(mock_jj_repo)
    assert success is False
    assert "Fetch failed" in message


@pytest.mark.asyncio
async def test_prune_remote_noop(jj_ops: JJOperations, mock_jj_repo: Path) -> None:
    """Test that prune is a no-op for jj"""
    success, message = await jj_ops.prune_remote(mock_jj_repo)
    assert success is True
    assert "doesn't require" in message


@pytest.mark.asyncio
async def test_cleanup_merged_branches(
    jj_ops: JJOperations, mock_jj_repo: Path
) -> None:
    """Test cleanup of merged bookmarks"""
    jj_ops._run_jj_async = AsyncMock(side_effect=[
        "feature1: tracking\nfeature2: tracking",  # bookmark list
        "",  # feature1 is merged (empty log)
        None,  # delete feature1
        "abc123",  # feature2 is not merged (has commits)
    ])

    success, message = await jj_ops.cleanup_merged_branches(mock_jj_repo)
    assert success is True
    assert "Deleted 1" in message or "No merged" in message


def test_parse_commit_list(jj_ops: JJOperations) -> None:
    """Test parsing commit list from jj log output"""
    output = "abc123|Add feature|John Doe|2024-01-01T00:00:00Z\ndef456|Fix bug|Jane Smith|2024-01-02T00:00:00Z"
    commits = jj_ops._parse_commit_list(output)

    assert len(commits) == 2
    assert commits[0].sha == "abc123"
    assert commits[0].message == "Add feature"
    assert commits[0].author == "John Doe"
    assert commits[1].sha == "def456"


def test_parse_branch_list(jj_ops: JJOperations) -> None:
    """Test parsing bookmark list from jj output"""
    output = "main: tracking\nfeature: local"
    branches = jj_ops._parse_branch_list(output, "main")

    assert len(branches) == 2
    assert branches[0].name == "main"
    assert branches[0].is_current is True
    assert branches[1].name == "feature"
    assert branches[1].is_current is False
