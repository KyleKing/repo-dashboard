from datetime import datetime
from pathlib import Path

import pytest

from repo_dashboard.modals import (
    HelpModal,
    _format_commits,
    _format_files,
    _format_pr_detail,
)
from repo_dashboard.models import CommitInfo, PRDetail


def test_format_commits_empty() -> None:
    result = _format_commits([])
    assert "No commits" in result


def test_format_commits_single() -> None:
    commits = [
        CommitInfo(
            sha="abc123",
            message="Fix bug",
            author="John Doe",
            date=datetime.now(),
        )
    ]
    result = _format_commits(commits)
    assert "abc123" in result
    assert "Fix bug" in result
    assert "John Doe" in result


def test_format_commits_multiple() -> None:
    commits = [
        CommitInfo(
            sha=f"abc{i}",
            message=f"Commit {i}",
            author=f"Author {i}",
            date=datetime.now(),
        )
        for i in range(5)
    ]
    result = _format_commits(commits)
    assert "abc0" in result
    assert "abc4" in result
    assert "Commit 0" in result
    assert "Commit 4" in result


def test_format_commits_truncation() -> None:
    commits = [
        CommitInfo(
            sha=f"abc{i}",
            message=f"Commit {i}",
            author=f"Author {i}",
            date=datetime.now(),
        )
        for i in range(15)
    ]
    result = _format_commits(commits, max_display=10)
    assert "abc0" in result
    assert "abc9" in result
    assert "... and 5 more" in result


def test_format_files_empty() -> None:
    result = _format_files([])
    assert "No files" in result


def test_format_files_single() -> None:
    result = _format_files(["file1.py"])
    assert "file1.py" in result


def test_format_files_multiple() -> None:
    result = _format_files(["file1.py", "file2.py", "file3.py"])
    assert "file1.py" in result
    assert "file2.py" in result
    assert "file3.py" in result


def test_format_files_with_prefix() -> None:
    result = _format_files(["file1.py", "file2.py"], prefix="  ")
    assert "  file1.py" in result
    assert "  file2.py" in result


def test_format_pr_detail_passing() -> None:
    pr = PRDetail(
        number=123,
        title="Fix bug",
        url="https://github.com/owner/repo/pull/123",
        state="OPEN",
        checks_status="passing",
        description="This is a test PR",
        unresolved_comments=0,
        additions=10,
        deletions=5,
    )
    result = _format_pr_detail(pr)
    assert "PR #123" in result
    assert "Fix bug" in result
    assert "OPEN" in result
    assert "✓" in result
    assert "+10" in result
    assert "-5" in result


def test_format_pr_detail_failing() -> None:
    pr = PRDetail(
        number=456,
        title="Add feature",
        url="https://github.com/owner/repo/pull/456",
        state="OPEN",
        checks_status="failing",
        description="Test",
        unresolved_comments=2,
        additions=20,
        deletions=10,
    )
    result = _format_pr_detail(pr)
    assert "PR #456" in result
    assert "✗" in result
    assert "Comments: 2" in result


def test_format_pr_detail_pending() -> None:
    pr = PRDetail(
        number=789,
        title="Update",
        url="https://github.com/owner/repo/pull/789",
        state="OPEN",
        checks_status="pending",
        description="Test",
        unresolved_comments=0,
        additions=5,
        deletions=3,
    )
    result = _format_pr_detail(pr)
    assert "PR #789" in result
    assert "○" in result


def test_format_pr_detail_unknown_status() -> None:
    pr = PRDetail(
        number=999,
        title="Test",
        url="https://github.com/owner/repo/pull/999",
        state="OPEN",
        checks_status=None,
        description="Test",
        unresolved_comments=0,
        additions=0,
        deletions=0,
    )
    result = _format_pr_detail(pr)
    assert "PR #999" in result
    assert "?" in result


def test_format_pr_detail_long_description() -> None:
    pr = PRDetail(
        number=111,
        title="Test",
        url="https://github.com/owner/repo/pull/111",
        state="OPEN",
        checks_status="passing",
        description="x" * 500,
        unresolved_comments=0,
        additions=0,
        deletions=0,
    )
    result = _format_pr_detail(pr)
    assert "..." in result
    assert len(result) < 600


def test_help_modal_creates_with_theme() -> None:
    modal = HelpModal("dark")
    assert modal.theme_name == "dark"


def test_help_modal_stores_theme_name() -> None:
    modal_dark = HelpModal("dark")
    modal_light = HelpModal("light")
    assert modal_dark.theme_name == "dark"
    assert modal_light.theme_name == "light"
