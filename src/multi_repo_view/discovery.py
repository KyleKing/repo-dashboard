from pathlib import Path


def discover_git_repos(base_paths: list[Path], max_depth: int) -> list[Path]:
    """Discover git repositories up to max_depth"""
    repos: set[Path] = set()

    for base_path in base_paths:
        if not base_path.exists() or not base_path.is_dir():
            continue

        if (base_path / ".git").exists():
            repos.add(base_path)
            continue

        _discover_recursive(base_path, max_depth, 0, repos)

    return sorted(repos)


def _discover_recursive(
    path: Path,
    max_depth: int,
    current_depth: int,
    repos: set[Path],
) -> None:
    if current_depth >= max_depth:
        return

    try:
        for item in path.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue

            if (item / ".git").exists():
                repos.add(item)
            else:
                _discover_recursive(item, max_depth, current_depth + 1, repos)
    except PermissionError:
        pass
