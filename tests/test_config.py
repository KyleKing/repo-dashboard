from pathlib import Path
from textwrap import dedent

import pytest

from multi_repo_view.config import (
    Config,
    _get_config_path,
    _get_xdg_config_home,
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
