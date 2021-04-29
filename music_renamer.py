import argparse
import os


def process_file(path):
    print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rename audio files based on metadata tags"
    )
    parser.add_argument("directory", help="The directory to rename audio files in")
    parser.add_argument(
        "-r", "--recursive", help="Recursive descend the file tree", action="store_true"
    )
    args = parser.parse_args()

    if args.recursive:
        for root, _, files in os.walk(args.directory):
            for file in files:
                process_file(os.path.join(root, file))
    else:
        for entry in os.scandir(args.directory):
            if entry.is_file():
                process_file(entry.path)
