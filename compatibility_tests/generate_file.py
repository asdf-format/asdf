import argparse
from pathlib import Path

from asdf.versioning import AsdfVersion

from common import generate_file


def parse_args():
    parser = argparse.ArgumentParser(description="Generate an ASDF file for library version compatibility testing")
    parser.add_argument("filename", help="the output filename")
    parser.add_argument("version", help="the ASDF Standard version to write")
    return parser.parse_args()


def main():
    args = parse_args()

    path = Path(args.filename)
    version = AsdfVersion(args.version)

    generate_file(path, version)


if __name__ == "__main__":
    main()
