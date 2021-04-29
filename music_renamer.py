import argparse
import os
from pathlib import Path
import sys

import mutagen


# def extract_tags(tags):
#     print(type(tags))

#     first_tags = []

#     for key, value in tags.items():
#         if value is list:
#             value = value[0]

#     return first_tags


def process_file(location, template, dry_run):
    path = Path(location)

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

        tracknumber = ""
        if "TRCK" in first_tags:
            # TRCK format optionally has a / to indicate the total number of tracks
            tracknumber = str(first_tags["TRCK"]).split("/")[0]
        elif "tracknumber" in first_tags:
            tracknumber = first_tags["tracknumber"]

        if len(tracknumber) > 0:
            first_tags["mr_padded_tracknumber"] = tracknumber.zfill(2)

        new_name = template.format(**first_tags)

        if dry_run:
            print(new_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rename audio files based on metadata tags"
    )
    parser.add_argument("directory", help="The directory to rename audio files in")
    parser.add_argument(
        "template", help="The template with which to rename the audio files"
    )
    parser.add_argument(
        "-r", "--recursive", help="Recursive descend the file tree", action="store_true"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        help="Print the new names of the files, but don't actually rename them",
        action="store_true",
    )
    args = parser.parse_args()

    if args.recursive:
        for root, _, files in os.walk(args.directory):
            for file in files:
                process_file(os.path.join(root, file), args.template, args.dry_run)
    else:
        for entry in os.scandir(args.directory):
            if entry.is_file():
                process_file(entry.path, args.template, args.dry_run)
