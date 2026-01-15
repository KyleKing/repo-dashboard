"""Visual regression tests using pytest-textual-snapshot.

These tests capture SVG screenshots of the TUI and compare them against baseline
snapshots stored in tests/__snapshots__/. Tests fail if the UI renders differently.

To update snapshots after intentional UI changes:
    uv run pytest tests/test_snapshots.py --snapshot-update

See README.md for full documentation.
"""

from pathlib import Path

import pytest

from multi_repo_view.app import MultiRepoViewApp


def test_empty_repo_warning(snap_compare, tmp_path: Path) -> None:
    """Snapshot test for warning when no repos are found"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    app = MultiRepoViewApp(
        scan_paths=[empty_dir],
        scan_depth=1,
        theme="dark",
    )

    assert snap_compare(app, terminal_size=(80, 24))


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


