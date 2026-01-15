"""Visual regression tests using pytest-textual-snapshot.

These tests capture SVG screenshots of the TUI and compare them against baseline
snapshots stored in tests/__snapshots__/. Tests fail if the UI renders differently.

To update snapshots after intentional UI changes:
    uv run pytest tests/test_snapshots.py --snapshot-update

See README.md for full documentation.
"""

import subprocess
from pathlib import Path

import pytest
from textual.pilot import Pilot

from multi_repo_view.app import MultiRepoViewApp


def _init_git_repo(repo_path: Path, branch: str = "main") -> None:
    """Initialize a git repo with basic config"""
    subprocess.run(["git", "init", "-b", branch], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)


def _create_commit(repo_path: Path, message: str) -> None:
    """Create a commit in the repo"""
    test_file = repo_path / "test.txt"
    test_file.write_text(message)
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True, capture_output=True)


def _create_branch(repo_path: Path, branch_name: str, checkout: bool = False) -> None:
    """Create a new branch"""
    subprocess.run(["git", "branch", branch_name], cwd=repo_path, check=True, capture_output=True)
    if checkout:
        subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True, capture_output=True)


def _create_stash(repo_path: Path, message: str) -> None:
    """Create a stash entry"""
    test_file = repo_path / "stash_test.txt"
    test_file.write_text("stash content")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "stash", "push", "-m", message], cwd=repo_path, check=True, capture_output=True)


def test_repo_list_view(snap_compare, tmp_path: Path) -> None:
    """Snapshot test for main repo list view with repos"""
    repo1 = tmp_path / "project-a"
    repo2 = tmp_path / "project-b"

    for repo in [repo1, repo2]:
        repo.mkdir()
        (repo / ".git").mkdir()

    app = MultiRepoViewApp(
        scan_paths=[tmp_path],
        scan_depth=1,
        theme="dark",
    )

    assert snap_compare(app, terminal_size=(80, 24))


def test_filter_sort_search_view(snap_compare, tmp_path: Path) -> None:
    """Snapshot test showing active filter, sort, and search badges"""
    repos = []
    for i, name in enumerate(["clean-repo", "dirty-repo", "ahead-repo", "example-app"]):
        repo = tmp_path / name
        repo.mkdir()
        _init_git_repo(repo)
        _create_commit(repo, "Initial commit")
        repos.append(repo)

    dirty_repo = tmp_path / "dirty-repo"
    (dirty_repo / "uncommitted.txt").write_text("uncommitted changes")

    app = MultiRepoViewApp(
        scan_paths=[tmp_path],
        scan_depth=1,
        theme="dark",
    )

    async def apply_filter_sort_search(pilot: Pilot) -> None:
        await pilot.pause(0.5)
        await pilot.press("f")
        await pilot.pause(0.2)
        await pilot.press("d")
        await pilot.pause(0.2)
        await pilot.press("s")
        await pilot.pause(0.2)
        await pilot.press("m")
        await pilot.pause(0.2)
        await pilot.press("/")
        await pilot.pause(0.2)
        pilot.app.query_one("#search-input").value = "clean"
        await pilot.pause(0.5)

    assert snap_compare(app, terminal_size=(100, 24), run_before=apply_filter_sort_search)


def test_repo_detail_view(snap_compare, tmp_path: Path) -> None:
    """Snapshot test showing branches and stashes in detail view"""
    repo = tmp_path / "example-repo"
    repo.mkdir()
    _init_git_repo(repo)
    _create_commit(repo, "Initial commit")

    _create_branch(repo, "feature/new-feature")
    _create_branch(repo, "bugfix/critical-fix")

    _create_stash(repo, "WIP: working on feature")
    _create_stash(repo, "Temporary changes")

    app = MultiRepoViewApp(
        scan_paths=[tmp_path],
        scan_depth=1,
        theme="dark",
    )

    async def navigate_to_detail(pilot: Pilot) -> None:
        await pilot.pause(0.5)
        await pilot.press("enter")
        await pilot.pause(1.0)

    assert snap_compare(app, terminal_size=(120, 30), run_before=navigate_to_detail)


