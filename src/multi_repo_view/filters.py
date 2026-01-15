from difflib import SequenceMatcher
from pathlib import Path

from multi_repo_view.models import FilterMode, RepoSummary, SortMode


def filter_repos(
    summaries: dict[Path, RepoSummary],
    mode: FilterMode,
    search_text: str = "",
) -> dict[Path, RepoSummary]:
    match mode:
        case FilterMode.ALL:
            filtered = summaries
        case FilterMode.DIRTY:
            filtered = _filter_dirty(summaries)
        case FilterMode.AHEAD:
            filtered = _filter_ahead(summaries)
        case FilterMode.BEHIND:
            filtered = _filter_behind(summaries)
        case FilterMode.HAS_PR:
            filtered = _filter_has_pr(summaries)
        case FilterMode.HAS_STASH:
            filtered = _filter_has_stash(summaries)
        case _:
            filtered = summaries

    if search_text:
        filtered = {
            path: summary
            for path, summary in filtered.items()
            if _fuzzy_match_name(summary.name, search_text)
        }

    return filtered


def _filter_dirty(summaries: dict[Path, RepoSummary]) -> dict[Path, RepoSummary]:
    return {
        path: summary
        for path, summary in summaries.items()
        if summary.ahead_count > 0 or summary.uncommitted_count > 0
    }


def _filter_ahead(summaries: dict[Path, RepoSummary]) -> dict[Path, RepoSummary]:
    return {
        path: summary for path, summary in summaries.items() if summary.ahead_count > 0
    }


def _filter_behind(summaries: dict[Path, RepoSummary]) -> dict[Path, RepoSummary]:
    return {
        path: summary
        for path, summary in summaries.items()
        if summary.behind_count > 0
    }


def _filter_has_pr(summaries: dict[Path, RepoSummary]) -> dict[Path, RepoSummary]:
    return {
        path: summary for path, summary in summaries.items() if summary.pr_info
    }


def _filter_has_stash(summaries: dict[Path, RepoSummary]) -> dict[Path, RepoSummary]:
    return {
        path: summary for path, summary in summaries.items() if summary.stash_count > 0
    }


def _fuzzy_match_name(name: str, search_text: str, threshold: float = 0.6) -> bool:
    if not search_text:
        return True
    name_lower = name.lower()
    search_lower = search_text.lower()
    if search_lower in name_lower:
        return True
    matcher = SequenceMatcher(None, name_lower, search_lower)
    return matcher.ratio() >= threshold


def sort_repos(
    paths: list[Path],
    summaries: dict[Path, RepoSummary],
    mode: SortMode,
) -> list[Path]:
    match mode:
        case SortMode.NAME:
            return _sort_by_name(paths, summaries)
        case SortMode.MODIFIED:
            return _sort_by_modified(paths, summaries)
        case SortMode.STATUS:
            return _sort_by_status(paths, summaries)
        case SortMode.BRANCH:
            return _sort_by_branch(paths, summaries)
        case _:
            return paths


def _sort_by_name(paths: list[Path], summaries: dict[Path, RepoSummary]) -> list[Path]:
    return sorted(paths, key=lambda p: summaries[p].name.lower())


def _sort_by_modified(
    paths: list[Path], summaries: dict[Path, RepoSummary]
) -> list[Path]:
    return sorted(paths, key=lambda p: summaries[p].last_modified, reverse=True)


def _sort_by_status(
    paths: list[Path], summaries: dict[Path, RepoSummary]
) -> list[Path]:
    return sorted(
        paths,
        key=lambda p: (
            not summaries[p].is_dirty,
            -summaries[p].uncommitted_count,
            summaries[p].name.lower(),
        ),
    )


def _sort_by_branch(
    paths: list[Path], summaries: dict[Path, RepoSummary]
) -> list[Path]:
    return sorted(
        paths, key=lambda p: (summaries[p].current_branch.lower(), summaries[p].name.lower())
    )
