import os
import sys
from pathlib import Path

from pydantic import BaseModel, field_validator

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


APP_NAME = "multi-repo-view"


def _get_xdg_config_home() -> Path:
    if xdg_config := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg_config)
    return Path.home() / ".config"


class RepoConfig(BaseModel):
    path: Path

    @field_validator("path", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()


class Settings(BaseModel):
    refresh_interval: int = 30


class Config(BaseModel):
    settings: Settings = Settings()
    repos: list[RepoConfig] = []


def _get_config_path() -> Path:
    return _get_xdg_config_home() / APP_NAME / "config.toml"


def load_config(config_path: Path | None = None) -> Config:
    path = config_path or _get_config_path()
    if not path.exists():
        return Config()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(data)


def get_repo_paths(config: Config) -> list[Path]:
    return [repo.path for repo in config.repos if repo.path.exists()]
