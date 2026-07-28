import argparse
import tomllib
from pathlib import Path
from typing import Optional, Union


def find_file_upwards(start_dir: Union[str, Path], filename: str) -> Optional[Path]:
    """
    Search for `filename` starting in `start_dir` and moving up through
    each parent directory until it's found or the filesystem root is reached.

    Args:
        start_dir: Directory to start searching from.
        filename: Name of the file to look for.

    Returns:
        Path to the file if found, otherwise None.
    """
    current = Path(start_dir).resolve()

    if not current.is_dir():
        raise NotADirectoryError(f"{current} is not a directory")

    for directory in [current, *current.parents]:
        candidate = directory / filename
        if candidate.is_file():
            return candidate

    return None


def main():
    parser = argparse.ArgumentParser(
        description="CLI tools for organizing your music library"
    )
    parser.add_argument("directory", help="the directory to rename audio files in")
    args = parser.parse_args()

    config_filepath = find_file_upwards(args.directory, "jamz.toml")
    print(config_filepath)

    if config_filepath is not None:
        with open(config_filepath, "rb") as infile:
            config = tomllib.load(infile)

        print(config)
    else:
        print("No config file found. Most be a `jamz.toml` in a parent directory")


if __name__ == "__main__":
    main()
