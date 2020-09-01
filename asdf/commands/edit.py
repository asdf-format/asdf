"""
Contains commands for dealing with exploded and imploded forms.
"""


import os
import sys

import asdf
from .. import generic_io
from .main import Command
from .. import AsdfFile


__all__ = ['edit']


class Edit(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
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
            help="Input file")

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

def get_yaml ( fname, return_yaml=False ) :
    '''
    Reads all bytes from an ASDF file up to the '\n...\n' delimiter, which 
    separates the YAML text from the binary data.  The location of the
    first byte of the delimiter is alwyas returned.  When requested, the 
    YAML text is also, returned.

    Parameters
    ----------
    fname : The input file name.
    return_yaml : the boolean flag to return the YAML text
    '''

    chunk_size = 1024                   # Arbitrary chunk to read

    # TODO - this needs to change to look for '\r\n' and not just '\n'.
    dstart = b'\x0a\x2e\x2e\x2e\x0a'    # The binary data delimiter - '\n...\n'
    dlen = len(dstart)                  # Length of binary delimiter

    with open(fname,"r+b") as fd :
        dfound = False                  # No data found, yet
        fbytes = fd.read(chunk_size)
        chunk_cnt = 0
        chunk_start = 0
        chunk_end = chunk_start + chunk_size - dlen
        while not dfound :
            for k in range(chunk_start,chunk_end) :
                if dstart==fbytes[k:k+dlen] :   # Check for the data delimiter
                    dfound = True
                    if return_yaml :
                        return k, fbytes[:k].decode('utf-8')
                    else :
                        return k, ''
            chunk_cnt = chunk_cnt + 1           # Count the number of chunks read
            cbytes = fd.read(chunk_size)
            if cbytes is None :
                return -1, ''   # EOF without finding delimiter
            fbytes += cbytes    # Save all bytes read
            chunk_start = chunk_cnt * chunk_size - dlen
            chunk_end = chunk_start + chunk_size

    return -1, ''   # EOF without finding delimiter

def get_yaml_name ( fname ) :
    '''
    Using the base ASDF name, create a corresponding YAML file name.

    Parameters
    ----------
    fname : The input file name.
    '''
    base, ext = os.path.splitext(fname)
    return base + '.yaml'

def get_asdf_name ( fname ) :
    '''
    Using the base YAML name, create a corresponding ASDF file name.

    Parameters
    ----------
    fname : The input file name.
    '''
    base, ext = os.path.splitext(fname)
    return base + '.asdf'

def validate_asdf_path ( fname ) :
    if not os.path.exists(fname) :
        print(f"Error: No file '{fname}' exists.")
        return False

    base, ext = os.path.splitext(fname)
    if ext!='.asdf' :
        return False
    return True

def validate_asdf_file ( fd ) :
    header_line = fd.read_until(b'\r?\n', 2, "newline", include=True)
    print(f"header_line = {header_line}")
    #self._file_format_version = cls._parse_header_line(header_line)
    file_format_version = asdf.parse_asdf_header_line(header_line)

    
def edit_func ( fname ) :
    """
    Creates a YAML file from an ASDF file.  The YAML file will contain only the
    YAML from the ASDF file.  The YAML text will be written to a YAML text file
    in the same, so from 'example.asdf' the file 'example.yaml' will be created.

    Parameters
    ----------
    fname : The input file name.
    """
    if not validate_asdf_path(fname) :
        return False

    fullpath = os.path.abspath(fname)
    fd = generic_io.get_file(fullpath, mode="r")
    validate_asdf_file(fd)

def edit_func_old ( fname ) :
    """
    Creates a YAML file from an ASDF file.  The YAML file will contain only the
    YAML from the ASDF file.  The YAML text will be written to a YAML text file
    in the same, so from 'example.asdf' the file 'example.yaml' will be created.

    Parameters
    ----------
    fname : The input file name.
    """

    # TODO - validate an ASDF file
    fullpath = os.path.abspath(fname)
    if not is_asdf_file(fullpath) :
        print("To use the '-e' option, as ASDF file must be inputted.")
        print(f"The file is not an ASDF: \n'{fullpath}'\n")
        return False

    # Get YAML from ASDF and its end location in the YAML file
    loc, yaml_string = get_yaml(fullpath,return_yaml=True)
    if -1==loc :
        print(f"Could not find the YAML of '{fullpath}'",file=sys.stderr)
        sys.exit(1)

    # Open YAML file
    fullyaml = get_yaml_name(fullpath)

    # Write all YAML from ASDF to YAML
    with open(fullyaml,"w") as fd :
        fd.write(f"{yaml_string}")
    # Tell user 
    delim = '*' * 65
    print(f"{delim}")
    print(f"A YAML text file has been created at:\n'{fullyaml}'\n")
    print("Edit this file in any text editor, then run the following command")
    print("to save YAML edits to the ASDF file:\n")
    print(f"'asdftool edit -s --infile {fullyaml}")
    print(f"\n{delim}")
    

def get_yaml_with_no_trailing_whitespace ( yamlpath ) :
    '''
    Get the YAML text from an ASDF file and remove any trailing whitespace.

    Parameters
    ----------
    fname : The input YAML file.
    '''
    with open(yamlpath,"r") as fd :
        yaml = fd.read()
        return yaml.rstrip()

    return ''

def save_func ( fname ) :
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
    """
    _1G = 1000**3   # 1 gig
    C   = 1         # constant multiple of gig
    SMALL_FILE_SIZE = C * _1G

    fullpath = os.path.abspath(fname)
    fullasdf = get_asdf_name(fullpath)
    if not is_yaml_file(fullpath) : # Validate YAML file
        print("To use the '-s' option, as YAML fle must be inputted.")
        print(f"The file is not a YAML: \n'{fullpath}'\n")
        return False

    # Check to see if a corresponding ASDF file exists
    if not os.path.exists(fullasdf) :
        print(f"Error: ASDF file does not exist '{fullasdf}'",file=sys.stderr)

    # Find end of YAML in ASDF
    loc, yaml_string = get_yaml(fullasdf,return_yaml=False)
    if -1==loc :
        print(f"Could not find the YAML of '{fullasdf}'",file=sys.stderr)
        sys.exit(1)

    # Read YAML
    yaml = get_yaml_with_no_trailing_whitespace(fullpath) 
    yaml_bytes = bytes(yaml,'utf-8')

    # TODO - validate YAML format and schema (maybe do this else where)

    # If larger than YAML in ASDF
    # TODO - Investigate python module fileinput
    #print(f"loc = {loc}, len(yaml) = {len(yaml)}")
    if loc == len(yaml_bytes) :
        #with open(fullasdf,"w") as fd :
        with open(fullasdf,"r+b") as fd :
            fd.write(yaml_bytes)
        print("Good write")
    elif loc > len(yaml_bytes) :
        diff = loc - len(yaml_bytes)
        # pad out YAML with spaces to ensure the entire YAML portion is overwritten 
        whitespace = ' ' * diff 
        bwrite = yaml_bytes + bytes(whitespace,'utf-8')
        with open(fullasdf,"r+b") as fd :
            fd.write(bwrite)
    else :
        # TODO - add functionality to detect the size of the ASDF file.  If it's
        #        smaller than a specific size rewrire the whole file.  If it's
        #        larger than a specific size tell the user to see if he wants a
        #        rewrite.
        print(f"\n\nYAML text ({len(yaml):,} bytes) in\n    '{fullpath}'")
        print(f"is larger than available space ({loc} bytes)  in")
        print(f"    {fullasdf}\n\n")
        asdf_size = os.path.getsize(fullasdf)
        if asdf_size < SMALL_FILE_SIZE :
            print(f"asdf_size = {asdf_size:,} and is less than {SMALL_FILE_SIZE:,} bytes")
        else :
            print(f"asdf_size = {asdf_size:,} and is greater than {SMALL_FILE_SIZE:,} bytes")
        print("\n")



def edit ( args ) :
    """
    Implode a given ASDF file, which may reference external data, back
    into a single ASDF file.

    Parameters
    ----------
    args : The command line arguments. 
    """
    if args.edit :
        return edit_func(args.fname)
    elif args.save :
        return save_func(args.fname)
    else :
        return print("Invalid arguments")









