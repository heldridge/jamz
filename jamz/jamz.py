import argparse
import os
from pathlib import Path
import tabulate

import mutagen


def process_file(location, template, dry_run, verbose):
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

        new_name = template.format(**first_tags)

        if not dry_run:
            os.rename(path, path.parent / new_name)

        return (path.name, new_name)

    else:
        if verbose:
            print(f"Skipping {path.name}, no identifiable tags")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Rename audio files based on metadata tags"
    )
    parser.add_argument("directory", help="The directory to rename audio files in")
    parser.add_argument(
        "template", help="The template with which to rename the audio files"
    )
    parser.add_argument(
        "-r",
        "--recursive",
        help="Recursively descend the file tree",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        help="Print the new names of the files, but don't actually rename them",
        action="store_true",
    )
    parser.add_argument(
        "-v", "--verbose", help="Enable verbose logging", action="store_true"
    )
    args = parser.parse_args()

    files = []
    if args.recursive:
        for root, _, walk_files in os.walk(args.directory):
            files += [os.path.join(root, file) for file in walk_files]
    else:
        files = [entry.path for entry in os.scandir(args.directory)]

    rename_table = []
    for file in files:
        result = process_file(file, args.template, args.dry_run, args.verbose)

        if result is not None:
            rename_table.append([result[0], "->", result[1]])

    if args.dry_run:
        print("\nDry run. Would have renamed the following files\n")
    else:
        print("\nRenamed the following files\n")
    print(tabulate.tabulate(rename_table, tablefmt="plain"))


if __name__ == "__main__":
    main()
