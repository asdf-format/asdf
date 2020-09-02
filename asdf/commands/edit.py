"""
Contains commands for lightweight text editing of an ASDF file.
Future work: Make this interactive editing.
"""

import io
import os
import sys

import asdf.constants as constants

from asdf.asdf import _parse_asdf_header_line
from asdf.asdf import _parse_asdf_comment_section
from asdf.asdf import _get_asdf_version_in_comments

from .. import AsdfFile
from .. import generic_io
from .. import reference
from .. import schema
from .. import yamlutil

from .main import Command

__all__ = ['edit']

#asdf_format_version = None
#asdf_standard_version = None


class Edit(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        """ Set up a command line argument parser for the edit subcommand.
        """
        desc_string = "Allows for easy editing of the YAML in an ASDF file.  " \
                      "For edit mode, the YAML portion of an ASDF file is"  \
                      "separated from the ASDF into a text file for easy" \
                      "editing.  For save mode, the edited text file is written" \
                      "to its ASDF file."

        # Set up the parser
        parser = subparsers.add_parser(
            str("edit"), help="Edit YAML portion of an ASDF file.",
            description=desc_string)

        # Need an input file
        parser.add_argument(
            '--infile', '-f', type=str, required=True, dest='fname',
            help="Input file (ASDF for -e option, YAML for -s option")

        # Need an output file
        parser.add_argument(
            '--outfile', '-o', type=str, required=True, dest='oname',
            help="Output file (YAML for -e option, ASDF for -s option")

        # The edit is either being performed or saved
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-s',action='store_true',dest='save',
            help="Saves a YAML text file to its ASDF file.  Requires an ASDF input file.")
        group.add_argument(
            '-e',action='store_true',dest='edit',
            help="Create a YAML text file for a ASDF file.  Requires a YAML input file.")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        """ Execute the edit subcommand.
        """
        return edit(args)


def is_yaml_file ( fname ) :
    '''
    Determines if a file is a YAML file based only on the file extension.

    Parameters
    ----------
    fname : The input file name.
    '''

    base, ext = os.path.splitext(fname)
    if '.yaml' != ext :
        return False
    return True


def is_asdf_file ( fname ) :
    '''
    Determines if a file is ASDF based on file extension and the first
    5 bytes of the file, which should be '#ASDF'.

    Parameters
    ----------
    fname : The input file name.
    '''

    base, ext = os.path.splitext(fname)
    if '.asdf' != ext :
        return False

    with open(fname,"r+b") as fd :
        first_string = "#ASDF"
        first_line = fd.read(len(first_string)).decode('utf-8')
        if first_string != first_line :
            return False

    return True


def is_validate_path_and_ext ( fname, wanted_ext=None ) :
    """ Validates the path exists and the extension is one wanted.

    Parameters
    ----------
    fname : The input file name.
    wanted_ext : List of extensions to check.
    """
    if not os.path.exists(fname) :
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


def is_validate_asdf_path ( fname ) :
    """ Validates fname path exists and has extension '.asdf'.

    Parameters
    ----------
    fname : The input file name.
    """
    ext = ['.asdf']
    if is_validate_path_and_ext(fname,ext) : 
        return True
    print(f"Error: '{fname}' should have extension '{ext[0]}'")
    return False


def is_validate_yaml_path ( fname ) :
    """ Validates fname path exists and has extension '.yaml'.

    Parameters
    ----------
    fname : The input file name.
    """
    ext = ['.yaml']
    if is_validate_path_and_ext(fname,ext) : 
        return True
    print(f"Error: '{fname}' should have extension '{ext[0]}'")
    return False


def validate_asdf_file ( fd ) :
    """ Makes sure the header line is the expected one, as well
    as getting the optional comment line.

    Parameters
    ----------
    fd : GenericFile
    """
    #global asdf_format_version 
    #global asdf_standard_version 
    ASDF_ID = b'#ASDF'

    header_line = fd.read_until(b'\r?\n', 2, "newline", include=True)
    if ASDF_ID!=header_line[:len(ASDF_ID)] :
        # Raise exception
        print("Invalid ASDF ID")
        sys.exit(1)
    
    #asdf_format_version = _parse_asdf_header_line(header_line)
    # Maybe validate ASDF format version
    comment_section = fd.read_until( b'(%YAML)|(' + constants.BLOCK_MAGIC + b')', 
                                     5, 
                                     "start of content", 
                                     include=False, 
                                     exception=False)
    # Maybe do the following for more validate.  But maybe not.
    #comments = _parse_asdf_comment_section(comment_section)
    #asdf_standard_version = _get_asdf_version_in_comments(comments)

    return header_line + comment_section 
    
def open_and_validate_asdf ( fname ) :
    """ Open and validate the ASDF file, as well as read in all the YAML
    that will be outputted to a YAML file.

    Parameters
    ----------
    fname : The input file name.
    """
    fullpath = os.path.abspath(fname)
    fd = generic_io.get_file(fullpath, mode="r")

    # Read the ASDF header and optional comments section
    header_and_comment = validate_asdf_file(fd)

    return fd, header_and_comment # Return GenericFile and ASDF header bytes.
    
def read_and_validate_yaml ( fd, fname ) :
    """ Get the YAML text from an ASDF formatted file.

    Parameters
    ----------
    fname : The input file name.
    fd : GenericFile for fname.
    """
    YAML_TOKEN = b'%YAML'
    token = fd.read(len(YAML_TOKEN))
    if token != YAML_TOKEN :
        # Raise exception
        print(f"Error: No YAML in '{fname}'")
        sys.exit(0)
    
    # Get YAML reader and content
    reader = fd.reader_until(constants.YAML_END_MARKER_REGEX, 
                             7, 
                             'End of YAML marker',  
                             include=True, 
                             initial_content=token)
    yaml_content = reader.read()

    # Create a YAML tree to validate
    # The YAML text must be converted to a stream.
    tree = yamlutil.load_tree(io.BytesIO(yaml_content))
    if tree is None:
        # Raise exception.
        print("Error: 'yamlutil.load_tree' failed to return a tree.")
        sys.exist(1)
    
    schema.validate(tree, None) # Failure raises and exception.

    return yaml_content

def edit_func ( fname, oname ) :
    """
    Creates a YAML file from an ASDF file.  The YAML file will contain only the
    YAML from the ASDF file.  The YAML text will be written to a YAML text file
    in the same, so from 'example.asdf' the file 'example.yaml' will be created.

    Parameters
    ----------
    fname : The input ASDF file name.
    oname : The output YAML file name.
    """
    if not is_validate_asdf_path(fname) :
        return False

    # 1. Validate input file is an ASDF file.
    fd, asdf_text = open_and_validate_asdf(fname)

    # 2. Read and validate the YAML of an ASDF file.
    yaml_text = read_and_validate_yaml(fd,fname)

    # 3. Open a YAML file for the ASDF YAML.
    if not is_yaml_file(oname) : 
        # Raise an exception
        print(f"Error: '{oname}' must have '.yaml' extension.")
        sys.exit(1)

    # 4. Write the YAML for the original ASDF file.
    with open(oname,"wb") as ofd :
        ofd.write(asdf_text)
        ofd.write(yaml_text)

    # 5. Output message to user.
    delim = '*' * 70
    print(f"\n{delim}")
    print("ASDF formatting and YAML schema validated.") 
    print(f"The text portion of '{fname}' is written to:")
    print(f"    '{oname}'")
    print(f"The file '{oname}' can be edited using your favorite text editor.")
    print("The edited text can then be saved to the ASDF file of your choice")
    print("using 'asdftool edit -s -f <edited text file> -o <ASDF file>.")
    print('-' * 70)
    print("Note: This is meant to be a lightweight text editing tool of")
    print("      ASDF .If the edited text is larger than the YAML portion")
    print("      of the ASDF file to be written to, the edits may not be")
    print("      able to saved.")
    print(f"{delim}\n")

    return

def save_func ( fname, oname ) :
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
    fname : The input YAML file.
    oname : The output ASDF file name.
    """
    _1G = 1000**3   # 1 gig
    C   = 1         # constant multiple of gig
    SMALL_FILE_SIZE = C * _1G

    if not is_validate_yaml_path(fname):
        return False

    if not is_validate_asdf_path(oname):
        return False

    # 1. Validate input file is an ASDF file.
    fd, asdf_text = open_and_validate_asdf(fname)

    # 2. Read and validate the YAML of an ASDF file.
    yaml_text = read_and_validate_yaml(fd,fname)

    edited_text = asdf_text + yaml_text

    # 3. Get text from ASDF file.
    # 4. Compare text sizes and maybe output.
    # 5. Output message to user.

    return

def edit ( args ) :
    """
    Implode a given ASDF file, which may reference external data, back
    into a single ASDF file.

    Parameters
    ----------
    args : The command line arguments. 
    """
    if args.edit :
        return edit_func(args.fname,args.oname)
    elif args.save :
        return save_func(args.fname,args.oname)
    else :
        return print("Invalid arguments")









