"""
Contains commands for lightweight text editing of an ASDF file.
"""

import io
import os
import re
import shutil

# Marked safe because the editor command is specified by an
# environment variable that the user controls.
import subprocess  # nosec
import sys
import tempfile

import yaml

from asdf import constants, generic_io, schema, util
from asdf._asdf import AsdfFile
from asdf._block import io as bio
from asdf._block.exceptions import BlockIndexError

from .main import Command

__all__ = ["edit"]


if sys.platform.startswith("win"):
    DEFAULT_EDITOR = "notepad"
else:
    DEFAULT_EDITOR = "vi"


class Edit(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        """
        Set up a command line argument parser for the edit subcommand.
        """
        # Set up the parser
        parser = subparsers.add_parser(
            "edit",
            description="Edit the YAML portion of an ASDF file in-place.",
        )

        # Need an input file
        parser.add_argument(
            "filename",
            help="Path to an ASDF file.",
        )

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        """
        Execute the edit subcommand.
        """
        return edit(args.filename)


def read_yaml(fd):
    """
    Read the YAML portion of an open ASDF file's content.

    Parameters
    ----------
    fd : GenericFile

    Returns
    -------
    bytes
        YAML content
    int
        total number of bytes available for YAML area
    bool
        True if the file contains binary blocks
    """
    # All ASDF files produced by this library, even the binary files
    # of an exploded ASDF file, include a YAML header, so we'll just
    # let this raise an error if the end marker can't be found.
    # Revisit this if someone starts producing files without a
    # YAML section, which the standard permits but is not possible
    # with current software.
    reader = fd.reader_until(
        constants.YAML_END_MARKER_REGEX,
        7,
        "End of YAML marker",
        include=True,
    )
    content = reader.read()

    reader = fd.reader_until(
        constants.BLOCK_MAGIC,
        len(constants.BLOCK_MAGIC),
        include=False,
        exception=False,
    )
    buffer = reader.read()

    contains_blocks = fd.peek(len(constants.BLOCK_MAGIC)) == constants.BLOCK_MAGIC

    return content, len(content) + len(buffer), contains_blocks


def write_edited_yaml_larger(path, new_content, version):
    """
    Rewrite an ASDF file, replacing the YAML portion with the
    specified YAML content and updating the block index if present.
    The file is assumed to contain binary blocks.

    Parameters
    ----------
    path : str
        Path to ASDF file
    content : bytes
        Updated YAML content
    """
    prefix = os.path.splitext(os.path.basename(path))[0] + "-"
    # Since the original file may be large, create the temporary
    # file in the same directory to avoid filling up the system
    # temporary area.
    temp_file = tempfile.NamedTemporaryFile(dir=os.path.dirname(path), prefix=prefix, suffix=".asdf", delete=False)
    try:
        temp_file.close()
        with generic_io.get_file(temp_file.name, mode="w") as fd:
            fd.write(new_content)
            # Allocate additional space for future YAML updates:
            pad_length = util.calculate_padding(len(new_content), True, fd.block_size)
            fd.fast_forward(pad_length)

            # now copy over ASDF block contents

            with generic_io.get_file(path) as original_fd:
                original_fd.seek_until(constants.BLOCK_MAGIC, len(constants.BLOCK_MAGIC))
                old_first_block_offset = original_fd.tell() - len(constants.BLOCK_MAGIC)
                new_first_block_offset = fd.tell()

                # check if the original file has a block index which we will need to update
                # as we're moving the blocks
                block_index_offset = bio.find_block_index(original_fd)
                if block_index_offset is None:
                    block_index = None
                    original_fd.seek(0, generic_io.SEEK_END)
                    blocks_end = original_fd.tell()
                else:
                    blocks_end = block_index_offset
                    try:
                        block_index = bio.read_block_index(original_fd, block_index_offset)
                    except BlockIndexError:
                        # the original index was invalid
                        block_index = None

                # copy over blocks byte-for-byte from old_first_block_offset to block_index_offset
                original_fd.seek(old_first_block_offset)
                block_size = min(fd.block_size, original_fd.block_size)
                n_bytes = blocks_end - old_first_block_offset
                for offset in range(0, n_bytes, block_size):
                    this_size = min(block_size, n_bytes - offset)
                    fd.write(original_fd.read(this_size))

                # update index
                if block_index is not None:
                    offset = new_first_block_offset - old_first_block_offset
                    updated_block_index = [i + offset for i in block_index]
                    bio.write_block_index(fd, updated_block_index)

        # Swap in the new version of the file atomically:
        shutil.copy(temp_file.name, path)
    finally:
        os.unlink(temp_file.name)


def write_edited_yaml(path, new_content, available_bytes):
    """
    Overwrite the YAML portion of an ASDF tree with the specified
    YAML content.  The content must fit in the space available.

    Parameters
    ----------
    path : str
        Path to ASDF file
    yaml_content : bytes
        Updated YAML content
    available_bytes : int
        Number of bytes available for YAML
    """
    # generic_io mode "rw" opens the file as "r+b":
    with generic_io.get_file(path, mode="rw") as fd:
        fd.write(new_content)

        pad_length = available_bytes - len(new_content)
        if pad_length > 0:
            fd.write(b"\0" * pad_length)


def edit(path):
    """
    Copy the YAML portion of an ASDF file to a temporary file, present
    the file to the user for editing, then update the original file
    with the modified YAML.

    Parameters
    ----------
    path : str
        Path to ASDF file
    """
    # Extract the YAML portion of the original file:
    with generic_io.get_file(path, mode="r") as fd:
        if fd.peek(len(constants.ASDF_MAGIC)) != constants.ASDF_MAGIC:
            print(f"Error: '{path}' is not an ASDF file.")
            return 1

        original_content, available_bytes, contains_blocks = read_yaml(fd)

    original_asdf_version = parse_asdf_version(original_content)
    original_yaml_version = parse_yaml_version(original_content)

    prefix = os.path.splitext(os.path.basename(path))[0] + "-"
    # We can't use temp_file's automatic delete because Windows
    # won't allow reading the file from the editor process unless
    # it is closed here.
    temp_file = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".yaml", delete=False)
    try:
        # Write the YAML to a temporary path:
        temp_file.write(original_content)
        temp_file.close()

        # Loop so that the user can correct errors in the edited file:
        while True:
            open_editor(temp_file.name)

            with open(temp_file.name, "rb") as f:
                new_content = f.read()

            if new_content == original_content:
                print("No changes made to file")
                return 0

            try:
                new_asdf_version = parse_asdf_version(new_content)
                new_yaml_version = parse_yaml_version(new_content)
            except Exception as e:
                print(f"Error: failed to parse ASDF header: {e!s}")
                choice = request_input("(c)ontinue editing or (a)bort? ", ["c", "a"])
                if choice == "a":
                    return 1

                continue

            if new_asdf_version != original_asdf_version or new_yaml_version != original_yaml_version:
                print("Error: cannot modify ASDF Standard or YAML version using this tool.")
                choice = request_input("(c)ontinue editing or (a)bort? ", ["c", "a"])
                if choice == "a":
                    return 1

                continue

            try:
                # check this is an ASDF file
                if new_content[: len(constants.ASDF_MAGIC)] != constants.ASDF_MAGIC:
                    msg = "Does not appear to be a ASDF file."
                    raise ValueError(msg)
                # read the tagged tree (which also checks if the YAML is valid)
                tagged_tree = util.load_yaml(io.BytesIO(new_content), tagged=True)
                # validate the tagged tree
                ctx = AsdfFile(version=new_asdf_version)
                schema.validate(tagged_tree, ctx=ctx, reading=True)
            except yaml.YAMLError as e:
                print("Error: failed to parse updated YAML:")
                print_exception(e)
                choice = request_input("(c)ontinue editing or (a)bort? ", ["c", "a"])
                if choice == "a":
                    return 1

                continue

            except schema.ValidationError as e:
                print("Warning: updated ASDF tree failed validation:")
                print_exception(e)
                choice = request_input("(c)ontinue editing, (f)orce update, or (a)bort? ", ["c", "f", "a"])
                if choice == "a":
                    return 1

                if choice == "c":
                    continue

            except Exception as e:
                print("Error: failed to read updated file as ASDF:")
                print_exception(e)
                choice = request_input("(c)ontinue editing or (a)bort? ", ["c", "a"])
                if choice == "a":
                    return 1

                continue

            # We've either opened the file without error, or
            # the user has agreed to ignore validation errors.
            # Break out of the loop so that we can update the
            # original file.
            break
    finally:
        os.unlink(temp_file.name)

    if len(new_content) <= available_bytes:
        # File has sufficient space allocated in the YAML area.
        write_edited_yaml(path, new_content, available_bytes)
    elif not contains_blocks:
        # File does not have sufficient space, but there are
        # no binary blocks, so we can just expand the file.
        write_edited_yaml(path, new_content, len(new_content))
    else:
        # File does not have sufficient space, and binary blocks
        # are present.
        print("Warning: updated YAML larger than allocated space.  File must be rewritten.")
        choice = request_input("(c)ontinue or (a)bort? ", ["c", "a"])
        if choice == "a":
            return 1

        write_edited_yaml_larger(path, new_content, new_asdf_version)

    return None


def parse_asdf_version(content):
    """
    Extract the ASDF Standard version from YAML content.

    Parameters
    ----------
    content : bytes

    Returns
    -------
    asdf.versioning.AsdfVersion
        ASDF Standard version
    """
    comments = AsdfFile._read_comment_section(generic_io.get_file(io.BytesIO(content)))
    return AsdfFile._find_asdf_version_in_comments(comments)


def parse_yaml_version(content):
    """
    Extract the YAML version from YAML content.

    Parameters
    ----------
    content : bytes

    Returns
    -------
    bytes
        YAML version string.
    """
    match = re.search(b"^%YAML (.*)$", content, flags=re.MULTILINE)
    if match is None:
        msg = "YAML version number not found"
        raise ValueError(msg)
    return match.group(1)


def print_exception(e):
    """
    Print an exception, indented 4 spaces and elided if too many lines.
    """
    lines = str(e).split("\n")
    if len(lines) > 20:
        lines = lines[0:20] + ["..."]
    for line in lines:
        print(f"    {line}")


def request_input(message, choices):
    """
    Request user input.

    Parameters
    ----------
    message : str
        Message to display
    choices : list of str
        List of recognized inputs
    """
    while True:
        choice = input(message).strip().lower()

        if choice in choices:
            return choice

        print(f"Invalid choice: {choice}")

    return None


def open_editor(path):
    """
    Launch an editor process with the file at path opened.
    """
    editor = os.environ.get("EDITOR", DEFAULT_EDITOR)
    # Marked safe because the editor command is specified by an
    # environment variable that the user controls.
    subprocess.run(f"{editor} {path}", check=True, shell=True)  # noqa: S602
