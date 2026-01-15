from datetime import datetime, timedelta
from pathlib import Path

import pytest

from multi_repo_view.filters import (
    _filter_ahead,
    _filter_behind,
    _filter_dirty,
    _filter_has_pr,
    _filter_has_stash,
    _fuzzy_match_name,
    _sort_by_branch,
    _sort_by_modified,
    _sort_by_name,
    _sort_by_status,
    filter_repos,
    sort_repos,
)
from multi_repo_view.models import (
    FilterMode,
    PRInfo,
    RepoStatus,
    RepoSummary,
    SortMode,
)


def _make_summary(
    name: str,
    ahead: int = 0,
    behind: int = 0,
    uncommitted: int = 0,
    has_pr: bool = False,
    stash: int = 0,
    modified_days_ago: int = 0,
    branch: str = "main",
) -> RepoSummary:
    pr_info = (
        PRInfo(
            number=123,
            title="Test PR",
            url="https://github.com/test/repo/pull/123",
            state="open",
            checks_status="success",
        )
        if has_pr
        else None
    )

    return RepoSummary(
        path=Path(f"/tmp/{name}"),
        name=name,
        current_branch=branch,
        ahead_count=ahead,
        behind_count=behind,
        uncommitted_count=uncommitted,
        stash_count=stash,
        worktree_count=0,
        pr_info=pr_info,
        last_modified=datetime.now() - timedelta(days=modified_days_ago),
        status=RepoStatus.OK,
    )


def test_filter_all_returns_all() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", uncommitted=5),
        Path("/tmp/repo2"): _make_summary("repo2"),
        Path("/tmp/repo3"): _make_summary("repo3", ahead=2),
    }
    result = filter_repos(summaries, FilterMode.ALL)
    assert len(result) == 3


def test_filter_dirty_keeps_dirty_repos() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", uncommitted=5),
        Path("/tmp/repo2"): _make_summary("repo2"),
        Path("/tmp/repo3"): _make_summary("repo3", ahead=2),
    }
    result = _filter_dirty(summaries)
    assert len(result) == 2
    assert Path("/tmp/repo1") in result
    assert Path("/tmp/repo3") in result
    assert Path("/tmp/repo2") not in result


def test_filter_dirty_includes_ahead() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", ahead=3),
    }
    result = _filter_dirty(summaries)
    assert len(result) == 1


def test_filter_dirty_includes_uncommitted() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", uncommitted=2),
    }
    result = _filter_dirty(summaries)
    assert len(result) == 1


def test_filter_ahead_keeps_only_ahead_repos() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", ahead=3),
        Path("/tmp/repo2"): _make_summary("repo2", behind=1),
        Path("/tmp/repo3"): _make_summary("repo3"),
    }
    result = _filter_ahead(summaries)
    assert len(result) == 1
    assert Path("/tmp/repo1") in result


def test_filter_behind_keeps_only_behind_repos() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", ahead=3),
        Path("/tmp/repo2"): _make_summary("repo2", behind=2),
        Path("/tmp/repo3"): _make_summary("repo3"),
    }
    result = _filter_behind(summaries)
    assert len(result) == 1
    assert Path("/tmp/repo2") in result


def test_filter_has_pr_keeps_only_pr_repos() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", has_pr=True),
        Path("/tmp/repo2"): _make_summary("repo2"),
        Path("/tmp/repo3"): _make_summary("repo3", has_pr=True),
    }
    result = _filter_has_pr(summaries)
    assert len(result) == 2
    assert Path("/tmp/repo1") in result
    assert Path("/tmp/repo3") in result


def test_filter_has_stash_keeps_only_stash_repos() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", stash=2),
        Path("/tmp/repo2"): _make_summary("repo2"),
        Path("/tmp/repo3"): _make_summary("repo3", stash=1),
    }
    result = _filter_has_stash(summaries)
    assert len(result) == 2
    assert Path("/tmp/repo1") in result
    assert Path("/tmp/repo3") in result


def test_sort_by_name_alphabetical() -> None:
    summaries = {
        Path("/tmp/zebra"): _make_summary("zebra"),
        Path("/tmp/apple"): _make_summary("apple"),
        Path("/tmp/mango"): _make_summary("mango"),
    }
    paths = list(summaries.keys())
    result = _sort_by_name(paths, summaries)
    names = [summaries[p].name for p in result]
    assert names == ["apple", "mango", "zebra"]


def test_sort_by_name_case_insensitive() -> None:
    summaries = {
        Path("/tmp/Zebra"): _make_summary("Zebra"),
        Path("/tmp/apple"): _make_summary("apple"),
        Path("/tmp/Mango"): _make_summary("Mango"),
    }
    paths = list(summaries.keys())
    result = _sort_by_name(paths, summaries)
    names = [summaries[p].name for p in result]
    assert names == ["apple", "Mango", "Zebra"]


def test_sort_by_modified_newest_first() -> None:
    summaries = {
        Path("/tmp/old"): _make_summary("old", modified_days_ago=10),
        Path("/tmp/new"): _make_summary("new", modified_days_ago=1),
        Path("/tmp/medium"): _make_summary("medium", modified_days_ago=5),
    }
    paths = list(summaries.keys())
    result = _sort_by_modified(paths, summaries)
    names = [summaries[p].name for p in result]
    assert names == ["new", "medium", "old"]


def test_sort_by_status_dirty_first() -> None:
    summaries = {
        Path("/tmp/clean"): _make_summary("clean"),
        Path("/tmp/dirty1"): _make_summary("dirty1", uncommitted=5),
        Path("/tmp/dirty2"): _make_summary("dirty2", uncommitted=2),
    }
    paths = list(summaries.keys())
    result = _sort_by_status(paths, summaries)
    names = [summaries[p].name for p in result]
    assert names[0] in ["dirty1", "dirty2"]
    assert names[-1] == "clean"


def test_sort_by_status_higher_uncommitted_first() -> None:
    summaries = {
        Path("/tmp/dirty1"): _make_summary("dirty1", uncommitted=2),
        Path("/tmp/dirty2"): _make_summary("dirty2", uncommitted=5),
    }
    paths = list(summaries.keys())
    result = _sort_by_status(paths, summaries)
    names = [summaries[p].name for p in result]
    assert names == ["dirty2", "dirty1"]


def test_sort_by_branch_alphabetical() -> None:
    summaries = {
        Path("/tmp/repo1"): _make_summary("repo1", branch="feature"),
        Path("/tmp/repo2"): _make_summary("repo2", branch="main"),
        Path("/tmp/repo3"): _make_summary("repo3", branch="develop"),
    }
    paths = list(summaries.keys())
    result = _sort_by_branch(paths, summaries)
    branches = [summaries[p].current_branch for p in result]
    assert branches == ["develop", "feature", "main"]


def test_sort_repos_with_mode() -> None:
    summaries = {
        Path("/tmp/zebra"): _make_summary("zebra"),
        Path("/tmp/apple"): _make_summary("apple"),
    }
    paths = list(summaries.keys())
    result = sort_repos(paths, summaries, SortMode.NAME)
    names = [summaries[p].name for p in result]
    assert names == ["apple", "zebra"]


def test_fuzzy_match_exact() -> None:
    assert _fuzzy_match_name("api-service", "api-service")


def test_fuzzy_match_partial() -> None:
    assert _fuzzy_match_name("api-service", "api")


def test_fuzzy_match_case_insensitive() -> None:
    assert _fuzzy_match_name("API-Service", "api")


def test_fuzzy_match_no_match() -> None:
    assert not _fuzzy_match_name("api-service", "xyz")


def test_fuzzy_match_empty_search() -> None:
    assert _fuzzy_match_name("any-name", "")


def test_fuzzy_match_threshold() -> None:
    result = _fuzzy_match_name("similar", "somilar", threshold=0.7)
    assert result


def test_filter_repos_with_search_text() -> None:
    """Test fuzzy search filtering"""
    summaries = {
        Path("/tmp/api-service"): _make_summary("api-service"),
        Path("/tmp/web-frontend"): _make_summary("web-frontend"),
        Path("/tmp/api-gateway"): _make_summary("api-gateway"),
    }
    result = filter_repos(summaries, FilterMode.ALL, "api")
    assert len(result) == 2
    assert Path("/tmp/api-service") in result
    assert Path("/tmp/api-gateway") in result
    assert Path("/tmp/web-frontend") not in result


def test_filter_repos_combined_filter_and_search() -> None:
    """Test filter mode + search work together"""
    summaries = {
        Path("/tmp/api-service"): _make_summary("api-service", uncommitted=1),
        Path("/tmp/web-frontend"): _make_summary("web-frontend", uncommitted=2),
        Path("/tmp/api-gateway"): _make_summary("api-gateway"),
    }
    result = filter_repos(summaries, FilterMode.DIRTY, "api")
    assert len(result) == 1
    assert Path("/tmp/api-service") in result
    assert Path("/tmp/web-frontend") not in result
    assert Path("/tmp/api-gateway") not in result


def test_filter_repos_empty_search() -> None:
    """Empty search shows all filtered repos"""
    summaries = {
        Path("/tmp/api"): _make_summary("api", uncommitted=1),
        Path("/tmp/web"): _make_summary("web", uncommitted=2),
    }
    result = filter_repos(summaries, FilterMode.DIRTY, "")
    assert len(result) == 2
    assert Path("/tmp/api") in result
    assert Path("/tmp/web") in result
