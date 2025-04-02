"""Save new requirements."""

import argparse
import os
import subprocess

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

path_requirements: str = os.path.join(BASE_DIR, "requirements.txt")
path_requirements_dev: str = os.path.join(BASE_DIR, "requirements_dev.txt")
path_requirements_new: str = os.path.join(BASE_DIR, "req_new.txt")


def check_req_files(file_paths: list[str]) -> None:
    """Check if the requirements files exists. Create them if not."""
    for file_path in file_paths:
        if not os.path.exists(file_path):
            with open(file_path, mode="w"):
                pass
            print(f"File {file_path} has just been created.")
        else:
            print(f"File {file_path} has already been created.")


def parse_args() -> argparse.Namespace:
    """Parse arguments from command line."""
    parser = argparse.ArgumentParser(
        description="Select requirements variant",
        epilog="Example: python req_handler.py -v dev",
    )
    parser.add_argument(
        "-v",
        "--requirements_variant",
        type=str,
        default="dev",
        help="provide a variant of requirements: dev or prod (default: dev)",
    )
    return parser.parse_args()


def pip_freeze() -> None:
    """Create a txt file with all actual libs."""
    with open(path_requirements_new, "w") as file:
        process = subprocess.run(
            ["pip", "freeze"],
            stdout=file,
            stderr=subprocess.PIPE,
            text=True,
        )

        if process.returncode == 0:
            print("The requirements have been successfully frozen.")
        else:
            print(
                f"An error has occurred. Completion code: {process.returncode}"
            )
            print(f"Error: {process.stderr}")


def read_requirements(file_path: str) -> set[str]:
    """Read requirements from a file."""
    with open(file=file_path, mode="r") as file:
        contents: str = file.read()

        print(f"File {file_path} read.")

        return set(
            [req for req in contents.splitlines() if not req.startswith("#")]
        )


def write_file(file_path: str, new_lines: set[str], mode: str = "a") -> None:
    """Write a new data to the file."""
    with open(file=file_path, mode=mode) as file:
        for line in sorted(new_lines):
            file.write(line + "\n")

    print(f"File {file_path} updated.")


def del_requirements(file_path: str, trash_reqs: set[str]) -> None:
    """Remove requirements from the file."""
    existing_reqs: set[str] = read_requirements(file_path)
    existing_reqs.difference_update(trash_reqs)

    if trash_reqs:
        print(f"Removed libs {trash_reqs} from file.")
    else:
        print("No libs to remove.")

    write_file(file_path=file_path, new_lines=existing_reqs, mode="w")


def get_libs() -> tuple[set[str], set[str], set[str]]:
    """Get all libs from txt files."""
    return (
        read_requirements(path_requirements),
        read_requirements(path_requirements_dev),
        read_requirements(path_requirements_new),
    )


def main(rewritable_file_path: str, vers_index: int) -> None:
    """Get new requirements."""
    check_req_files(file_paths=[path_requirements, path_requirements_dev])
    pip_freeze()

    libs: tuple = get_libs()
    new_reqs: set = libs[2] - (libs[0] | libs[1])
    trash_reqs: set = libs[vers_index].difference(libs[2])

    write_file(file_path=rewritable_file_path, new_lines=new_reqs)
    del_requirements(rewritable_file_path, trash_reqs)

    os.remove(path=path_requirements_new)
    print(f"File {path_requirements_new} removed.")


if __name__ == "__main__":
    local_parser: argparse.Namespace = parse_args()
    print(f"Selected reqs variant: {local_parser.requirements_variant}")

    path_file_to_rewrite = path_requirements_dev
    vers_index: int = 1

    if local_parser.requirements_variant == "prod":
        path_file_to_rewrite = path_requirements
        vers_index = 0

    main(path_file_to_rewrite, vers_index)
