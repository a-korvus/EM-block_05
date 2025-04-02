"""Simple script to check your code."""

import subprocess as sp
from argparse import ArgumentParser, Namespace


def parse_args() -> Namespace:
    """Parse arguments from command line."""
    parser = ArgumentParser(
        description="Specify the path to the files or dirs to be scanned.",
        epilog="Example: python -m lint -p main.py",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default=".",
        help="provide the path to files (default: root dir as '.')",
    )
    return parser.parse_args()


def run_linters(path: str) -> None:
    """Run code check."""
    linters: tuple[str, ...] = (
        "isort",
        "black",
        "flake8",
        "mypy",
    )
    commands: list[str] = [linter + f" {path}" for linter in linters]

    for cmd in commands:
        print(f"Run {cmd}")
        result: sp.CompletedProcess = sp.run(cmd, shell=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: command failed: {cmd}")
            break


if __name__ == "__main__":
    local_parser: Namespace = parse_args()
    print(f"Specified path: {local_parser.path}")
    run_linters(path=local_parser.path)
