"""
Contains commands for lightweight text editing of an ASDF file.
Future work: Make this interactive editing.
"""

import io
import os
import struct
import sys

import asdf.constants as constants

from .. import generic_io
from .. import schema
from .. import yamlutil

from .main import Command

__all__ = ["edit"]


class Edit(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        """
        Set up a command line argument parser for the edit subcommand.
        """
        desc_string = (
            "Allows for easy editing of the YAML in an ASDF file.  "
            "For edit mode, the YAML portion of an ASDF file is "
            "separated from the ASDF into a text file for easy "
            "editing.  For save mode, the edited text file is written "
            "to its ASDF file."
        )

        # Set up the parser
        parser = subparsers.add_parser(
            "edit",
            help="Edit YAML portion of an ASDF file.",
            description=desc_string,
        )

        # Need an input file
        parser.add_argument(
            "--infile",
            "-f",
            type=str,
            required=True,
            dest="fname",
            help="Input file (ASDF for -e option, YAML for -s option)",
        )

        # Need an output file
        parser.add_argument(
            "--outfile",
            "-o",
            type=str,
            required=True,
            dest="oname",
            help="Output file (YAML for -e option, ASDF for -s option)",
        )

        """
        # Validate input YAML.  Optional, since this could be what's being corrected.
        parser.add_argument(
            "--validate",
            "-v",
            type=bool,
            action="store_true",
            dest="validate",
            help="Validate input YAML format.",
        )
        """

        # The edit is either being performed or saved
        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            "-s",
            action="store_true",
            dest="save",
            help="Saves a YAML text file to an ASDF file.  Requires a "
            "YAML input file and ASDF output file.",
        )

        group.add_argument(
            "-e",
            action="store_true",
            dest="edit",
            help="Create a YAML text file for a ASDF file.  Requires a ASDF input file.",
        )

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        """
        Execute the edit subcommand.
        """
        return edit(args)


def is_yaml_file(fname):
    """
    Determines if a file is a YAML file based only on the file extension.

    Parameters
    ----------
    fname : str
        Input file name.

    Return
    ------
    bool
    """

    base, ext = os.path.splitext(fname)
    if ".yaml" != ext and ".yml" != ext:
        return False
    return True


def is_valid_path_and_ext(fname, wanted_ext=None):
    """
    Validates the path exists and the extension is one wanted.

    Parameters
    ----------
    fname : str
        Input file name.
    wanted_ext : List of str, optional
        Extensions to check

    Return
    ------
    bool
    """
    if not os.path.exists(fname):
        print(f"Error: No file '{fname}' exists.")
        return False

    # Simply validates the path existence
    if wanted_ext is None:
        return True

    # Make sure the extension is one desired.
    base, ext = os.path.splitext(fname)
    if ext not in wanted_ext:
        return False

    return True


def is_valid_asdf_path(fname):
    """
    Validates fname path exists and has extension '.asdf'.

    Parameters
    ----------
    fname : str
        ASDF file name

    Return
    ------
    bool
    """
    ext = [".asdf"]
    if is_valid_path_and_ext(fname, ext):
        return True
    print(f"Error: '{fname}' should have extension '{ext[0]}'")
    return False


def is_valid_yaml_path(fname):
    """
    Validates fname path exists and has extension '.yaml'.

    Parameters
    ----------
    fname : str
        ASDF file name

    Return
    ------
    bool
    """
    ext = [".yaml", ".yml"]
    if is_valid_path_and_ext(fname, ext):
        return True
    print(f"Error: '{fname}' should have extension '{ext[0]}'")
    return False


def check_asdf_header(fd):
    """
    Makes sure the header line is the expected one, as well
    as getting the optional comment line.

    Parameters
    ----------
    fd : GenericFile

    Return
    ------
    bytes
        The ASDF header line and the ASDF comment.
    """

    header_line = fd.read_until(b"\r?\n", 2, "newline", include=True)
    if not header_line.startswith(constants.ASDF_MAGIC):
        print("Invalid ASDF ID")
        sys.exit(1)

    comment_section = fd.read_until(
        b"(%YAML)|(" + constants.BLOCK_MAGIC + b")",
        5,
        "start of content",
        include=False,
        exception=False,
    )

    return header_line + comment_section


def open_and_check_asdf_header(fname):
    """
    Open and validate the ASDF file, as well as read in all the YAML
    that will be outputted to a YAML file.

    Parameters
    ----------
    fname : str
        Input file name

    Return
    ------
    GenericFile
        File descriptor for ASDF file.
    bytes
        ASDF header and ASDF comments.
    """
    fullpath = os.path.abspath(fname)
    fd = generic_io.get_file(fullpath, mode="r")

    # Read the ASDF header and optional comments section
    header_and_comment = check_asdf_header(fd)

    return fd, header_and_comment  # Return GenericFile and ASDF header bytes.


def read_and_validate_yaml(fd, fname, validate_yaml):
    """
    Get the YAML text from an ASDF formatted file.

    Parameters
    ----------
    fname : str
        Input file name
    fd : GenericFile 
        for fname.

    Return
    ------
    bytes
        The YAML portion of an ASDF file.
    """
    YAML_TOKEN = b"%YAML"
    token = fd.read(len(YAML_TOKEN))
    if token != YAML_TOKEN:
        print(f"Error: No YAML in '{fname}'")
        sys.exit(0)

    # Get YAML reader and content
    reader = fd.reader_until(
        constants.YAML_END_MARKER_REGEX,
        7,
        "End of YAML marker",
        include=True,
        initial_content=token,
    )
    yaml_content = reader.read()

    if validate_yaml:
        # Create a YAML tree to validate
        # The YAML text must be converted to a stream.
        tree = yamlutil.load_tree(io.BytesIO(yaml_content))
        if tree is None:
            print("Error: 'yamlutil.load_tree' failed to return a tree.")
            sys.exist(1)

        schema.validate(tree)  # Failure raises an exception.

    return yaml_content


def edit_func(fname, oname):
    """
    Creates a YAML file from an ASDF file.  The YAML file will contain only the
    YAML from the ASDF file.  The YAML text will be written to a YAML text file
    in the same, so from 'example.asdf' the file 'example.yaml' will be created.

    Parameters
    ----------
    fname : str
        Input ASDF file name
    oname : str
        Output YAML file name.
    """
    if not is_valid_asdf_path(fname):
        return False

    if not is_yaml_file(oname):
        print("A YAML file is expected, with '.yaml' or '.yml' extension.")
        sys.exit(1)

    # Validate input file is an ASDF file.
    fd, asdf_text = open_and_check_asdf_header(fname)

    # Read and validate the YAML of an ASDF file.
    yaml_text = read_and_validate_yaml(fd, fname, False)
    fd.close()

    # Write the YAML for the original ASDF file.
    with open(oname, "wb") as ofd:
        ofd.write(asdf_text)
        ofd.write(yaml_text)

    # Output message to user.
    delim = "*" * 70
    print(f"\n{delim}")
    print("ASDF formatting and YAML schema validated.")
    print(f"The text portion of '{fname}' is written to:")
    print(f"    '{oname}'")
    print(f"The file '{oname}' can be edited using your favorite text editor.")
    print("The edited text can then be saved to the ASDF file of your choice")
    print("using 'asdftool edit -s -f <edited text file> -o <ASDF file>.")
    print(f"{delim}\n")

    return


def write_block_index(fd, index):
    """
    Write the block index to an ASDF file.

    Parameters
    ----------
    fd - The output file to write the block index.
    index - A list of locations for each block.
    """
    if len(index) < 1:
        return

    # TODO - this needs to be changed to use constants.py and pyyaml
    bindex_hdr = b"#ASDF BLOCK INDEX\n%YAML 1.1\n---\n"
    fd.write(bindex_hdr)
    for idx in index:
        ostr = f"- {idx}\n"
        fd.write(ostr.encode("utf-8"))
    end = b"..."
    fd.write(end)
    return


def find_first_block(fname):
    """
    Finds the location of the first binary block in an ASDF file.

    Parameters
    ----------
    fname : str
        Input ASDF file name.

    Return
    ------
    int
        Location, in bytes, of the first binary block.
    """
    with generic_io.get_file(fname, mode="r") as fd:
        reader = fd.reader_until(
            constants.BLOCK_MAGIC,
            7,
            "First binary block",
            include=False,
        )
        content_to_first_block = reader.read()
    return len(content_to_first_block) 

def copy_binary_blocks(ofd, ifd):
    """
    Copies the binary blocks from the input ASDF to the output ASDF.

    Parameters
    ----------
    ofd: file descriptor
        Output ASDF file.
    ifd: file descriptor
        Input ASDF file.
    """
    block_index = [] # A new block index needs to be computed.

    while True:
        token_length = ifd.read(6)
        if not token_length.startswith(constants.BLOCK_MAGIC):
            ifd.seek(-6,os.SEEK_CUR)
            break


def write_edited_yaml_larger(fname, oname, edited_yaml, first_block_loc):
    """
    The edited YAML is too large to simply overwrite the exiting YAML in an 
    ASDF file, so the ASDF file needs to be rewritten.

    Parameters
    ----------
    oname : str
        Input ASDF file name.
    edited_yaml : byte string
        The edited YAML to be saved to an ASDF file
    first_block_location : the location in the ASDF file for the first binary
                           block
    """
    tmp_oname = oname + "tmp"

    ifd = open(oname,"rb")
    ifd.seek(first_block_loc)

    ofd = open(tmp_oname,"wb")
    ofd.write(edited_yaml)

    pad_length = 10000  
    padding = b'\0' * pad_length
    ofd.write(padding)

    copy_binary_blocks(ofd, ifd)

    ifd.close()
    ofd.close()
    # os.replace(tmp_oname,oname)


def write_edited_yaml(fname, oname, edited_yaml, first_block_loc):
    """
    Write the edited YAML is to an existing ASDF file.

    Parameters
    ----------
    oname : str
        Input ASDF file name.
    edited_yaml : byte string
        The edited YAML to be saved to an ASDF file
    first_block_location : the location in the ASDF file for the first binary
                           block
    """
    if len(edited_yaml) < first_block_loc:
        # The YAML in the ASDF can simply be overwritten
        pad_length = first_block_loc - len(edited_yaml)
        padding = b'\0' * pad_length
        with open(oname, "r+b") as fd:
            fd.write(edited_yaml)
            fd.write(padding)
    elif len(edited_yaml) == first_block_loc:
        # The YAML in the ASDF can simply be overwritten
        with open(oname, "r+b") as fd:
            fd.write(edited_yaml)
    else:
        write_edited_yaml_larger(fname, oname, edited_yaml, first_block_loc)  


def save_func(fname, oname):
    """
    Checks to makes sure a corresponding ASDF file exists.  This is done by
        seeing if a file of the same name with '.asdf' as an extension exists.
    Checks to makes sure fname is a valid YAML file.
    If the YAML text is smaller than the YAML text in the ASDF file
        overwrite the YAML in the ASDF file.
    If the YAML text is smaller than the YAML text in the ASDF file
        If the file is small, then rewrite file.
        If the file is large, ask if rewrite is desired.

    Parameters
    ----------
    fname : str
        Input YAML file name.
    oname : str
        The output ASDF file name.
    """

    if not is_valid_yaml_path(fname):
        return False

    if not is_valid_asdf_path(oname):
        return False

    # Validate input file is an ASDF formatted YAML.
    ifd, iasdf_text = open_and_check_asdf_header(fname)
    iyaml_text = read_and_validate_yaml(ifd, fname, True)
    ifd.close()
    edited_text = iasdf_text + iyaml_text

    loc = find_first_block(oname)
    write_edited_yaml(fname, oname, edited_text, loc)


def edit(args):
    """
    Implode a given ASDF file, which may reference external data, back
    into a single ASDF file.

    Parameters
    ----------
    args : The command line arguments.
    """
    if args.edit:
        return edit_func(args.fname, args.oname)
    elif args.save:
        return save_func(args.fname, args.oname)
    else:
        return print("Invalid arguments")
