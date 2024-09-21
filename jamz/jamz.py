import argparse
import os
from pathlib import Path
import re
import shutil
import textwrap

import mutagen
import tabulate


def process_file(location, template, dry_run, verbose, ignore_errors):
    path = Path(location)

    if path.is_dir():
        return None

    file = mutagen.File(path)
    if file is not None:
        # Mutagen can have multiple values for each tag, so we just take the first
        # Not all tag formats use lists for values though, so we attempt to take the
        # first, and then just fall back to using the original value
        first_tags = {}
        for key, value in file.tags.items():
            try:
                value = value[0]
            except TypeError:
                pass

            first_tags[key] = value

        # Add custom padded tracknumber tag
        tracknumber = ""
        if "TRCK" in first_tags:
            # TRCK format optionally has a / to indicate the total number of tracks
            tracknumber = str(first_tags["TRCK"]).split("/")[0]
        elif "tracknumber" in first_tags:
            tracknumber = first_tags["tracknumber"]

        if len(tracknumber) > 0:
            first_tags["jamz_padded_tracknumber"] = tracknumber.zfill(2)

        # Add custom original suffix tag
        first_tags["jamz_original_suffix"] = path.suffix

        try:
            new_name = template.format(**first_tags)
        except Exception as e:
            if not ignore_errors:
                raise (e)
            if verbose:
                print(
                    f"Skipping {path.name}, error applying template: {type(e).__name__}: {e}"
                )
            return None

        if not dry_run:
            os.rename(path, path.parent / new_name)

        return (path.name, new_name)

    else:
        if verbose:
            print(f"Skipping {path.name}, no identifiable tags")
    return None


def rename(args):
    files = []
    if args.recursive:
        for root, _, walk_files in os.walk(args.directory):
            files += [os.path.join(root, file) for file in walk_files]
    else:
        files = [entry.path for entry in os.scandir(args.directory)]

    rename_table = []
    for file in files:
        result = process_file(
            file, args.template, args.dry_run, args.verbose, args.ignore_errors
        )

        if result is not None:
            rename_table.append([result[0], "->", result[1]])

    if args.dry_run:
        print("\nDry run. Would have renamed the following files\n")
    else:
        print("\nRenamed the following files\n")
    print(tabulate.tabulate(rename_table, tablefmt="plain"))

def sanitize(s):
    # Characters to replace
    chars_to_replace = r'[/\\:*?"<>|]'
    
    # Replace problematic characters with underscore
    sanitized = re.sub(chars_to_replace, '_', s)
    
    # Remove trailing spaces and periods (Windows restriction)
    sanitized = sanitized.rstrip(' .')
    
    return sanitized

def add(args):
    files = []
    if args.recursive:
        for root, _, walk_files in os.walk(args.source_directory):
            files += [os.path.join(root, file) for file in walk_files]
    else:
        files = [entry.path for entry in os.scandir(args.source_directory)]

    target_directory = Path(args.target_directory)
    movement_table = {} 
    for file in files:
        path = Path(file)

        if path.is_dir():
            continue
        mutagen_file = mutagen.File(path)
        if mutagen_file is not None:
            tags = mutagen_file.tags
            if 'artist' in tags:
                artist = tags['artist'][0]
            elif 'TPE1' in tags:
                artist = tags['TPE1'][0]
            else:
                print(f"Failed to find artist for file {path}, skipping...")
                continue

            if 'album' in tags:
                album = tags['album'][0]
            elif 'TALB' in tags:
                album = tags['TALB'][0]
            else:
                print(f"Failed to find album for file {path}, skipping...")
                continue
            new_path = target_directory / sanitize(artist) / sanitize(album)
            movement_table[path] = new_path

    if args.dry_run:
        print("Dry run, would have moved the following files:")
        for old, new in movement_table.items():
            print(old, "-->", new)
    else:
        for old, new in movement_table.items():
            os.makedirs(new, exist_ok = True)
            shutil.move(old, new)


def main():
    tags_table = [
        [
            "jamz_padded_tracknumber",
            "The tracknumber (if found) padded to two digits (e.g. 2 -> 02)",
        ],
        [
            "jamz_original_suffix",
            "The original suffix of the file, e.g. '.flac' if the file is named 'song.flac'",
        ],
    ]

    indented_table = textwrap.indent(
        tabulate.tabulate(tags_table, tablefmt="plain"), "  "
    )

    parser = argparse.ArgumentParser(
        description="CLI tools for organizing your music library"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    rename_parser = subparsers.add_parser(
        "rename",
        help="Rename audio files based on their tags",
        description="Rename audio files based on metadata tags",
        epilog=f"special tags:\n{indented_table}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    rename_parser.add_argument(
        "directory", help="The directory to rename audio files in"
    )
    rename_parser.add_argument(
        "template", help="The template with which to rename the audio files"
    )
    rename_parser.add_argument(
        "-r",
        "--recursive",
        help="Recursively descend the file tree",
        action="store_true",
    )
    rename_parser.add_argument(
        "-d",
        "--dry-run",
        help="Print the new names of the files, but don't actually rename them",
        action="store_true",
    )
    rename_parser.add_argument(
        "-i",
        "--ignore-errors",
        help="Skip over files that lead to errors",
        action="store_true",
    )
    rename_parser.add_argument(
        "-v", "--verbose", help="Enable verbose logging", action="store_true"
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Move audio files into your existing collection",
        description="Move audio files into your existing collection",
    )
    add_parser.add_argument(
        "source_directory", help="The directory to move audio files from"
    )
    add_parser.add_argument(
        "target_directory", help="The directory to move audio files to"
    )
    add_parser.add_argument(
        "-r",
        "--recursive",
        help="recursively descend the file tree",
        action="store_true",
    )
    add_parser.add_argument(
            "-d",
            "--dry-run",
            help="Print the locations files would be moved to, but don't actually move them",
            action="store_true"
            )
    args = parser.parse_args()

    if args.command == "rename":
        rename(args)
    elif args.command == "add":
        add(args)
    else:
        print(f"Unrecognized command '{args.command}'")


if __name__ == "__main__":
    main()
