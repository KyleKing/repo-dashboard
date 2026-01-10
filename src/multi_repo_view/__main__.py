import argparse
import os
from pathlib import Path

from multi_repo_view.app import MultiRepoViewApp

CONFIG_ENV_VAR = "MULTI_REPO_VIEW_CONFIG"


def _resolve_config_path(cli_arg: Path | None) -> Path | None:
    if cli_arg:
        return cli_arg.expanduser().resolve()
    if env_path := os.environ.get(CONFIG_ENV_VAR):
        return Path(env_path).expanduser().resolve()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-repo git status viewer")
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help=f"Path to config file (env: {CONFIG_ENV_VAR}, default: ~/.config/multi-repo-view/config.toml)",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=Path,
        help="Path to scan for git repositories (looks for all */.git/ directories)",
    )
    args = parser.parse_args()

    config_path = _resolve_config_path(args.config)
    scan_path = args.path.expanduser().resolve() if args.path else None
    app = MultiRepoViewApp(config_path=config_path, scan_path=scan_path)
    app.run()


if __name__ == "__main__":
    main()
