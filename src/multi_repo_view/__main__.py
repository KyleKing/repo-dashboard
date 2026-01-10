import argparse
from pathlib import Path

from multi_repo_view.app import MultiRepoViewApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-repo git status viewer")
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to config file (default: ~/.config/multi-repo-view/config.toml)",
    )
    args = parser.parse_args()

    app = MultiRepoViewApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
