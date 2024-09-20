import argparse
import os
from pathlib import Path
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

    parser = argparse.ArgumentParser(description="CLI tools for organizing your music library")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    

    rename_parser = subparsers.add_parser(
        "rename",
        help="Rename audio files based on their tags",
        description="Rename audio files based on metadata tags",
        epilog=f"special tags:\n{indented_table}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    rename_parser.add_argument("directory", help="The directory to rename audio files in")
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
    args = parser.parse_args()
   
    if args.command == "rename":
        rename(args)
    else:
        print(f"Unrecognized command '{args.command}'")

if __name__ == "__main__":
    main()
