import os
import shutil

import numpy as np

import asdf
from asdf import AsdfFile
from asdf.commands import main
from ...tests.helpers import get_file_sizes, assert_tree_match


"""
Three tests are defined.  

1. Run the command 'asdftool edit -e' to create a YAML file, simulating
   the steps a user would make to start editing an ASDF file.
2. Run the command 'asdftool edit -s' to save YAML edits such that the
   edited YAML will have the same or fewer characters as the original
   ASDF file, so will be overwritten in place with the space character
   used as any buffer, to consume all the memory on disk the YAML takes
   up in the ASDF file.
2. Run the command 'asdftool edit -s' to save YAML edits such that the
   edited YAML will have the more characters than the original ASDF file.
   This triggers a rewrite of the file, since there isn't enough 'room' 
   on disk to accomadate the edited YAML.  The resultant YAML will be 
   rewritten with a buffer (using the space character as buffer) to 
   accomodate future edits.  If a block index existed in the original ASDF
   file, it will need to be recomputed and if one didn't exist, it will be
   added to the resultant ASDF file.  
"""


def create_base_asdf(tmpdir):
    """
    In the test temp directory, create a base ASDF file to edit
    and test against.
    """
    seq = np.arange(100)

    # Store the data in an arbitrarily nested dictionary
    tree = {
        "foo": 42,
        "name": "Monty",
        "sequence": seq,
    }

    fname = "test_edit_base.asdf"
    oname = os.path.join(tmpdir, fname)
    if os.path.exists(oname):
        os.remove(oname)
    af = asdf.AsdfFile(tree)
    af.write_to(oname)

    return oname


def create_edit_equal(base_yaml):
    """
    The YAML from the base ASDF file will have a 'foo' value of 42.  Create
    an edited YAML file with this value being 41.  This will create an edited
    YAML file with the same number of characters in the YAML section as was in
    the original ASDF file.
    """
    with open(base_yaml, "r") as fd:
        lines = fd.readlines()

    base, ext = os.path.splitext(base_yaml)
    oname = f"{base}_edit_equal.yaml"
    if os.path.exists(oname):
        os.remove(oname)
    with open(oname, "w") as fd:
        for l in lines:
            if "foo" in l:
                print("foo: 41", file=fd)  #  Change a value
            else:
                fd.write(l)

    return oname


def create_edit_smaller(base_yaml):
    """
    The YAML from the base ASDF file will have a 'foo' value of 42.  Create
    an edited YAML file with this value being 41.  This will create an edited
    YAML file with the same number of characters in the YAML section as was in
    the original ASDF file.
    """
    with open(base_yaml, "r") as fd:
        lines = fd.readlines()

    base, ext = os.path.splitext(base_yaml)
    oname = f"{base}_edit_smaller.yaml"
    if os.path.exists(oname):
        os.remove(oname)
    with open(oname, "w") as fd:
        for l in lines:
            if "foo" in l:
                print("foo: 2", file=fd)  #  Change a value
            else:
                fd.write(l)

    return oname


def create_edit_larger(base_yaml):
    """
    The YAML from the base ASDF file will have a 'foo' value.  After this
    line, add another line.  This will create an edited YAML file that will
    have more characters than the YAML portion of the original ASDF file.
    """
    with open(base_yaml, "r") as fd:
        lines = fd.readlines()

    base, ext = os.path.splitext(base_yaml)
    oname = f"{base}_edit_larger.yaml"
    if os.path.exists(oname):
        os.remove(oname)
    with open(oname, "w") as fd:
        for l in lines:
            fd.write(l)
            if "foo" in l:
                print("bar: 13", file=fd)  # Add a line

    return oname


def copy_base_asdf_equal(base_asdf):
    """
    Create an ASDF file from the base ASDF file to test the editing of the
    YAML portion with equal number of YAML characters.
    """
    base, ext = os.path.splitext(base_asdf)
    oname = f"{base}_equal.asdf"
    if os.path.exists(oname):
        os.remove(oname)
    shutil.copyfile(base_asdf, oname)

    return oname


def copy_base_asdf_smaller(base_asdf):
    """
    Create an ASDF file from the base ASDF file to test the editing of the
    YAML portion with equal number of YAML characters.
    """
    base, ext = os.path.splitext(base_asdf)
    oname = f"{base}_smaller.asdf"
    if os.path.exists(oname):
        os.remove(oname)
    shutil.copyfile(base_asdf, oname)

    return oname


def copy_base_asdf_larger(base_asdf):
    """
    Create an ASDF file from the base ASDF file to test the editing of the
    YAML portion with a larger number of YAML characters.
    """
    base, ext = os.path.splitext(base_asdf)
    oname = f"{base}_larger.asdf"
    if os.path.exists(oname):
        os.remove(oname)
    shutil.copyfile(base_asdf, oname)

    return oname


def test_edits(tmpdir):
    #        Test:
    # Create base ASDF file for testing
    tmpdir = "/Users/kmacdonald/tmp"
    asdf_base = create_base_asdf(tmpdir)

    # Create base YAML file from base ASDF file
    base, ext = os.path.splitext(asdf_base)
    yaml_base = f"{base}.yaml"
    # Run: asdftool edit -e -f {asdf_base} -o {yaml_base}
    args = ["edit", "-e", "-f", f"{asdf_base}", "-o", f"{yaml_base}"]
    main.main_from_args(args)

    # Test smaller
    # Create ASDF file to edit with larger sized YAML
    asdf_smaller = copy_base_asdf_smaller(asdf_base)

    # Create edited YAML file with larger number of characters
    yaml_smaller = create_edit_smaller(yaml_base)

    # Run: asdftool edit -s -f {yaml_larger} -o {asdf_larger}
    args = ["edit", "-s", "-f", f"{yaml_smaller}", "-o", f"{asdf_smaller}"]
    main.main_from_args(args)

    af_smaller = asdf.open(asdf_smaller)
    assert af_smaller.tree["foo"] == 2
    assert os.path.getsize(asdf_smaller) == os.path.getsize(asdf_base)

    # Test equal
    # Create ASDF file to edit with equal sized YAML
    asdf_equal = copy_base_asdf_equal(asdf_base)

    # Create edited YAML file with equal number of characters
    yaml_equal = create_edit_equal(yaml_base)

    # Save edits to ASDF files
    # Run: asdftool edit -s -f {yaml_equal} -o {asdf_equal}
    args = ["edit", "-s", "-f", f"{yaml_equal}", "-o", f"{asdf_equal}"]
    print(f"args = {args}")
    main.main_from_args(args)

    af_equal = asdf.open(asdf_equal)
    assert af_equal.tree["foo"] == 41
    assert os.path.getsize(asdf_equal) == os.path.getsize(asdf_base)

    # Test larger
    # Create ASDF file to edit with larger sized YAML
    asdf_larger = copy_base_asdf_larger(asdf_base)

    # Create edited YAML file with larger number of characters
    yaml_larger = create_edit_larger(yaml_base)

    # Run: asdftool edit -s -f {yaml_larger} -o {asdf_larger}
    args = ["edit", "-s", "-f", f"{yaml_larger}", "-o", f"{asdf_larger}"]
    main.main_from_args(args)

    af_larger = asdf.open(asdf_larger)
    assert "bar" in af_larger.tree
    assert os.path.getsize(asdf_larger) - os.path.getsize(asdf_base) > 10000
