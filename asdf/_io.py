"""
Low-level input/output routines for AsdfFile instances
"""

import contextlib
import io
import pathlib

from . import _version, constants, generic_io, versioning, yamlutil
from ._block.manager import Manager as BlockManager
from .exceptions import DelimiterNotFoundError
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


def read_header_line(gf):
    try:
        header_line = gf.read_until(b"\r?\n", 2, "newline", include=True)
    except DelimiterNotFoundError as e:
        msg = "Does not appear to be a ASDF file."
        raise ValueError(msg) from e

    return parse_header_line(header_line)


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


def find_asdf_version_in_comments(comments, default=None):
    for comment in comments:
        parts = comment.split()
        if len(parts) == 2 and parts[0] == constants.ASDF_STANDARD_COMMENT:
            try:
                version = versioning.AsdfVersion(parts[1].decode("ascii"))
            except ValueError:
                pass
            else:
                return version

    return default


@contextlib.contextmanager
def maybe_close(fd, mode=None, uri=None):
    if mode not in [None, "r", "rw"]:
        msg = f"Unrecognized asdf mode '{mode}'. Must be either 'r' or 'rw'"
        raise ValueError(msg)

    if isinstance(fd, (str, pathlib.Path)):
        mode = mode or "r"
        generic_file = generic_io.get_file(fd, mode=mode, uri=uri)
        try:
            yield generic_file
        except Exception as e:
            generic_file.close()
            raise e
    elif isinstance(fd, generic_io.GenericFile):
        yield fd
    else:
        if mode is None:
            # infer from fd
            if isinstance(fd, io.IOBase):
                mode = "rw" if fd.writable() else "r"
            else:
                mode = "r"
        yield generic_io.get_file(fd, mode=mode, uri=uri)


def read_tree_and_blocks(gf, lazy_load, memmap, validate_checksums):
    token = gf.read(4)
    tree = None
    blocks = BlockManager(uri=gf.uri, lazy_load=lazy_load, memmap=memmap, validate_checksums=validate_checksums)
    if token == b"%YAM":
        reader = gf.reader_until(
            constants.YAML_END_MARKER_REGEX,
            7,
            "End of YAML marker",
            include=True,
            initial_content=token,
        )
        tree = yamlutil.load_tree(reader)
        blocks.read(gf, after_magic=False)
    elif token == constants.BLOCK_MAGIC:
        blocks.read(gf, after_magic=True)
    elif token != b"":
        msg = "ASDF file appears to contain garbage after header."
        raise OSError(msg)

    return tree, blocks


def open_asdf(fd, uri=None, mode=None, lazy_load=True, memmap=False, validate_checksums=False):
    with maybe_close(fd, mode, uri) as generic_file:
        file_format_version = read_header_line(generic_file)
        comments = read_comment_section(generic_file)
        tree, blocks = read_tree_and_blocks(generic_file, lazy_load, memmap, validate_checksums)
        return file_format_version, comments, tree, blocks
