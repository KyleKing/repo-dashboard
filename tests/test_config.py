from pathlib import Path
from textwrap import dedent

import pytest

from multi_repo_view.config import (
    Config,
    _get_config_path,
    _get_xdg_config_home,
    discover_git_repos,
    get_repo_paths,
    load_config,
)


def test_get_xdg_config_home_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    result = _get_xdg_config_home()
    assert result == Path.home() / ".config"


def test_get_xdg_config_home_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    result = _get_xdg_config_home()
    assert result == Path("/custom/config")


def test_get_config_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    result = _get_config_path()
    assert result == Path.home() / ".config" / "multi-repo-view" / "config.toml"


def test_load_config_missing_file(tmp_path: Path) -> None:
    config = load_config(tmp_path / "nonexistent.toml")
    assert config.repos == []
    assert config.settings.refresh_interval == 30


def test_load_config_valid(tmp_path: Path) -> None:
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        dedent(f"""\
        [settings]
        refresh_interval = 60

        [[repos]]
        path = "{repo1}"

        [[repos]]
        path = "{repo2}"
        """)
    )
    config = load_config(config_file)
    assert len(config.repos) == 2
    assert config.settings.refresh_interval == 60
    assert config.repos[0].path == repo1


def test_load_config_expands_tilde(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        dedent("""\
        [[repos]]
        path = "~/some/path"
        """)
    )
    config = load_config(config_file)
    assert config.repos[0].path == Path.home() / "some" / "path"


def test_get_repo_paths_filters_nonexistent(tmp_path: Path) -> None:
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    config = Config(
        repos=[
            {"path": str(existing_dir)},
            {"path": str(tmp_path / "nonexistent")},
        ]
    )
    paths = get_repo_paths(config)
    assert paths == [existing_dir]


def test_discover_git_repos_empty_dir(tmp_path: Path) -> None:
    result = discover_git_repos(tmp_path)
    assert result == []


def test_discover_git_repos_nonexistent_path(tmp_path: Path) -> None:
    result = discover_git_repos(tmp_path / "nonexistent")
    assert result == []


def test_discover_git_repos_finds_repos(tmp_path: Path) -> None:
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    not_a_repo = tmp_path / "not-a-repo"

    repo1.mkdir()
    (repo1 / ".git").mkdir()

    repo2.mkdir()
    (repo2 / ".git").mkdir()

    not_a_repo.mkdir()

    result = discover_git_repos(tmp_path)
    assert len(result) == 2
    assert repo1 in result
    assert repo2 in result
    assert not_a_repo not in result


def test_discover_git_repos_sorted(tmp_path: Path) -> None:
    for name in ["zebra", "apple", "middle"]:
        repo_dir = tmp_path / name
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

    result = discover_git_repos(tmp_path)
    assert [r.name for r in result] == ["apple", "middle", "zebra"]


def test_get_repo_paths_with_scan_path(tmp_path: Path) -> None:
    config_repo = tmp_path / "config-repo"
    config_repo.mkdir()

    scan_base = tmp_path / "scan"
    scan_base.mkdir()

    scanned_repo1 = scan_base / "repo1"
    scanned_repo1.mkdir()
    (scanned_repo1 / ".git").mkdir()

    scanned_repo2 = scan_base / "repo2"
    scanned_repo2.mkdir()
    (scanned_repo2 / ".git").mkdir()

    config = Config(repos=[{"path": str(config_repo)}])

    paths = get_repo_paths(config, scan_base)
    assert len(paths) == 3
    assert config_repo in paths
    assert scanned_repo1 in paths
    assert scanned_repo2 in paths


def test_get_repo_paths_with_scan_path_no_duplicates(tmp_path: Path) -> None:
    scan_base = tmp_path / "scan"
    scan_base.mkdir()

    repo = scan_base / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    config = Config(repos=[{"path": str(repo)}])

    paths = get_repo_paths(config, scan_base)
    assert len(paths) == 1
    assert paths[0] == repo
