import argparse
from pathlib import Path

from multi_repo_view.app import MultiRepoViewApp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-repo git status viewer (K9s-inspired TUI)"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path.cwd()],
        help="Paths to scan for git repositories (default: current directory)",
    )
    parser.add_argument(
        "--depth",
        "-d",
        type=int,
        default=1,
        choices=range(1, 21),
        metavar="1-20",
        help="Directory scan depth (default: 1, max: 20)",
    )
    parser.add_argument(
        "--theme",
        "-t",
        choices=["dark", "light"],
        default="dark",
        help="Color theme (default: dark)",
    )
    args = parser.parse_args()

    paths = [p.expanduser().resolve() for p in args.paths]
    app = MultiRepoViewApp(
        scan_paths=paths,
        scan_depth=args.depth,
        theme=args.theme,
    )
    app.run()


if __name__ == "__main__":
    main()
