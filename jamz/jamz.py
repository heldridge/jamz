from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TypeVar

import mutagen
import tabulate
import tomllib
from cattrs import structure

import custom_tag
from config import Config

T = TypeVar("T")


@dataclass
class ErrorFile:
    path: Path
    exception: Exception


@dataclass
class RenameTarget:
    source: Path
    destination: Path


def import_file(module_name: str, path: str):
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")

    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def find_file_upwards(start_dir: str | Path, filename: str) -> Path | None:
    """Seaches upwards in the filetree for a file name.

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
        message = f"{current} is not a directory"
        raise NotADirectoryError(message)

    for directory in [current, *current.parents]:
        candidate = directory / filename
        if candidate.is_file():
            return candidate

    return None


def get_tags(
    f: Path, config: Config, user_tags: list[custom_tag.CustomTag]
) -> dict[str, str] | None:
    mf = mutagen.File(f)

    # Base tags
    tags: dict[str, str] = {}
    if mf is not None:
        if mf.tags is not None:
            for key, value in mf.tags.items():
                try:
                    v_0 = value[0]
                except TypeError:
                    continue

                tags[key] = v_0

        # Custom tags
        for ct in custom_tag.default_custom_tags + user_tags:
            if (val := ct.creator.make_tag(f, tags, config)) is not None:
                tags[ct.name] = val

        return tags

    return None


def run_rename(
    config: Config,
    user_tags: list[custom_tag.CustomTag],
    directory: str,
    *,
    dry_run: bool,
) -> None:
    files: list[Path] = []

    for root, _, walk_files in os.walk(directory):
        files += [Path(root) / Path(wf) for wf in walk_files]

    bad_files: list[Path] = []
    error_files: list[ErrorFile] = []
    rename_files: list[RenameTarget] = []
    for f in files:
        tags = get_tags(f, config, user_tags)

        if tags is None:
            bad_files.append(f)
        else:
            try:
                template = config.path_template
                albumid = tags.get("jamz_musicbrainz_albumid")
                if albumid is not None and albumid in config.template_overrides:
                    template = config.template_overrides[albumid]

                new_path = Path(template.format(**tags))
                rename_files.append(RenameTarget(f, new_path))
            except Exception as e:
                error_files.append(ErrorFile(f, e))

    rename_targets: list[RenameTarget] = list(
        filter(
            lambda rf: rf.destination.resolve() != rf.source.resolve(),
            rename_files,
        ),
    )
    rename_table: list[list[str]] = [
        [str(rt.source), "->", str(rt.destination)] for rt in rename_targets
    ]

    if len(rename_targets) > 0:
        if dry_run:
            print("Dry run. Would have moved the following files:")
        else:
            print("Moving the following files:")
        print(tabulate.tabulate(rename_table, tablefmt="plain"))

    if len(error_files) > 0:
        print("\nSkipped the following files due to formatting errors:")
        for ef in error_files:
            print(ef.path, ef.exception)

    if len(bad_files) > 0:
        print(
            (
                "\nSkipped the following files due to not being in a recognized audio "
                "format"
            ),
        )
        for bf in bad_files:
            print(bf)

    if not dry_run:
        for rt in rename_targets:
            rt.destination.parent.mkdir(parents=True, exist_ok=True)
            Path.rename(rt.source, rt.destination)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI tools for organizing your music library",
    )
    parser.add_argument("directory", help="the directory to rename audio files in")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--plugins", "-p", type=str, nargs="*")
    args = parser.parse_args()

    config_filepath = find_file_upwards(args.directory, "jamz.toml")
    print("Using config at:", config_filepath)

    if config_filepath is not None:
        with Path.open(config_filepath, "rb") as infile:
            config = structure(tomllib.load(infile), Config)

        user_tags = []

        if (plugin_paths := args.plugins) is not None:
            for i, plugin_path in enumerate(plugin_paths):
                m = import_file(f"user_plugin_{i}", plugin_path)
                user_tags += m.custom_tags

        run_rename(config, user_tags, args.directory, dry_run=args.dry_run)

    else:
        print("No config file found. Create a `jamz.toml` in a parent directory.")


if __name__ == "__main__":
    main()
