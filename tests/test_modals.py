from datetime import datetime
from pathlib import Path

import pytest

from multi_repo_view.modals import _format_commits, _format_files, _format_pr_detail
from multi_repo_view.models import CommitInfo, PRDetail


class TestFormatCommits:
    def test_format_commits_empty(self):
        result = _format_commits([])
        assert "No commits" in result

    def test_format_commits_single(self):
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

    def test_format_commits_multiple(self):
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

    def test_format_commits_truncation(self):
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


class TestFormatFiles:
    def test_format_files_empty(self):
        result = _format_files([])
        assert "No files" in result

    def test_format_files_single(self):
        result = _format_files(["file1.py"])
        assert "file1.py" in result

    def test_format_files_multiple(self):
        result = _format_files(["file1.py", "file2.py", "file3.py"])
        assert "file1.py" in result
        assert "file2.py" in result
        assert "file3.py" in result

    def test_format_files_with_prefix(self):
        result = _format_files(["file1.py", "file2.py"], prefix="  ")
        assert "  file1.py" in result
        assert "  file2.py" in result


class TestFormatPRDetail:
    def test_format_pr_detail_passing(self):
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

    def test_format_pr_detail_failing(self):
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

    def test_format_pr_detail_pending(self):
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

    def test_format_pr_detail_unknown_status(self):
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

    def test_format_pr_detail_long_description(self):
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
