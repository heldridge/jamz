import argparse
import tabulate
import tomllib
from pathlib import Path
from typing import Optional, Union, TypeVar, Any
from dataclasses import dataclass
from cattrs import structure
import os
import mutagen
import pathvalidate

T = TypeVar("T")


@dataclass
class Config:
    path_template: str
    album_overrides: dict[str, str]
    template_overrides: dict[str, str]


@dataclass
class ErrorFile:
    path: Path
    exception: Exception


@dataclass
class RenameTarget:
    source: Path
    destination: Path


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


def clean_disk_number(value: str) -> Optional[str]:
    """Turn '3/12' or '3' into the int 3."""
    value = str(value)
    head = value.split("/")[0].strip()
    return head if head.isdigit() else None


def get_first_present_key_value(d: dict[Any, T], keys: list) -> Optional[T]:
    for k in keys:
        if k in d:
            return d[k]


def get_tracknumber(tags: dict[str, str]) -> Optional[str]:
    if "TRCK" in tags:
        return str(tags["TRCK"]).split("/")[0]
    elif "tracknumber" in tags:
        return tags["tracknumber"]
    elif "trkn" in tags:
        return str(tags["trkn"][0])


def get_albumartist(tags: dict[str, str]) -> Optional[str]:
    return get_first_present_key_value(tags, ["albumartist", "TPE2", "aART"])


def get_album(tags: dict[str, str], album_overrides: dict[str, str]) -> Optional[str]:

    albumid = tags.get("jamz_musicbrainz_albumid")
    if albumid is not None and albumid in album_overrides:
        return album_overrides[tags["musicbrainz_albumid"]]

    return get_first_present_key_value(tags, ["album", "TALB", "©alb"])


def get_title(tags: dict[str, str]) -> Optional[str]:
    return get_first_present_key_value(tags, ["title", "TIT2", "©nam"])


def get_musicbrainz_albumid(tags: dict[str, str]) -> Optional[str]:
    return get_first_present_key_value(
        tags, ["musicbrainz_albumid", "TXXX:MusicBrainz Album Id"]
    )


def get_disk_number(tags: dict[str, str]) -> Optional[str]:
    dirty_dn = get_first_present_key_value(tags, ["TPOS", "discnumber"])
    if dirty_dn is not None:
        return clean_disk_number(dirty_dn)


def get_tags(f: Path, album_overrides: dict[str, str]) -> Optional[dict[str, str]]:
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
        tags["jamz_original_suffix"] = f.suffix
        albumid = get_musicbrainz_albumid(tags)
        if albumid is not None:
            tags["jamz_musicbrainz_albumid"] = albumid

        tracknumber = get_tracknumber(tags)
        if tracknumber is not None:
            tags["jamz_padded_tracknumber"] = tracknumber.zfill(2)

        albumartist = get_albumartist(tags)
        if albumartist is not None:
            tags["jamz_sanitized_albumartist"] = pathvalidate.sanitize_filename(
                albumartist
            )
        album = get_album(tags, album_overrides)
        if album is not None:
            tags["jamz_sanitized_album"] = pathvalidate.sanitize_filename(album)

        title = get_title(tags)
        if title is not None:
            tags["jamz_sanitized_title"] = pathvalidate.sanitize_filename(title)

        disc_number = get_disk_number(tags)
        if disc_number is not None:
            tags["jamz_disc_number"] = disc_number

        return tags

    return None


def run_rename(config: Config, directory: str, dry_run: bool):
    files: list[Path] = []

    for root, _, walk_files in os.walk(directory):
        files += [Path(root) / Path(wf) for wf in walk_files]

    bad_files: list[Path] = []
    error_files: list[ErrorFile] = []
    rename_files: list[RenameTarget] = []
    for f in files:
        tags = get_tags(f, config.album_overrides)

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
        filter(lambda rf: rf.destination.resolve() != rf.source.resolve(), rename_files)
    )
    rename_table: list[list[str]] = []
    for rf in rename_targets:
        rename_table.append([str(rf.source), "->", str(rf.destination)])

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
            "\nSkipped the following files due to not being in a recognized audio format"
        )
        for bf in bad_files:
            print(bf)

    if not dry_run:
        for rt in rename_targets:
            rt.destination.parent.mkdir(parents=True, exist_ok=True)
            os.rename(rt.source, rt.destination)


def main():
    parser = argparse.ArgumentParser(
        description="CLI tools for organizing your music library"
    )
    parser.add_argument("directory", help="the directory to rename audio files in")
    parser.add_argument("--dry-run", "-d", action="store_true")
    args = parser.parse_args()

    config_filepath = find_file_upwards(args.directory, "jamz.toml")
    print(config_filepath)

    if config_filepath is not None:
        with open(config_filepath, "rb") as infile:
            config = structure(tomllib.load(infile), Config)
        run_rename(config, args.directory, args.dry_run)

    else:
        print("No config file found. Create a `jamz.toml` in a parent directory.")


if __name__ == "__main__":
    main()
