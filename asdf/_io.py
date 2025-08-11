"""
Low-level input/output routines for AsdfFile instances
"""

from . import _version, constants, versioning
from .tags.core import Software


def get_asdf_library_info():
    """
    Get information about asdf to include in the asdf_library entry
    in the Tree.
    """
    return Software(
        {
            "name": "asdf",
            "version": _version.version,
            "homepage": "http://github.com/asdf-format/asdf",
            "author": "The ASDF Developers",
        },
    )


def parse_header_line(line):
    """
    Parses the header line in a ASDF file to obtain the ASDF version.
    """
    parts = line.split()
    if len(parts) != 2 or parts[0] != constants.ASDF_MAGIC:
        msg = "Does not appear to be a ASDF file."
        raise ValueError(msg)

    try:
        version = versioning.AsdfVersion(parts[1].decode("ascii"))
    except ValueError as err:
        msg = f"Unparsable version in ASDF file: {parts[1]}"
        raise ValueError(msg) from err

    if version != versioning._FILE_FORMAT_VERSION:
        msg = f"Unsupported ASDF file format version {version}"
        raise ValueError(msg)

    return version


def read_comment_section(fd):
    """
    Reads the comment section, between the header line and the
    Tree or first block.
    """
    content = fd.read_until(
        b"(%YAML)|(" + constants.BLOCK_MAGIC + b")",
        5,
        "start of content",
        include=False,
        exception=False,
    )

    comments = []

    lines = content.splitlines()
    for line in lines:
        if not line.startswith(b"#"):
            msg = "Invalid content between header and tree"
            raise ValueError(msg)
        comments.append(line[1:].strip())

    return comments


def find_asdf_version_in_comments(comments):
    for comment in comments:
        parts = comment.split()
        if len(parts) == 2 and parts[0] == constants.ASDF_STANDARD_COMMENT:
            try:
                version = versioning.AsdfVersion(parts[1].decode("ascii"))
            except ValueError:
                pass
            else:
                return version

    return None
