import os
import re
import shutil

import numpy as np
import pytest

import asdf
from asdf import AsdfFile
from asdf.commands import main
from ...tests.helpers import get_file_sizes, assert_tree_match


def _create_base_asdf(version, oname):
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

    af = asdf.AsdfFile(tree, version=version)
    af.write_to(oname)


def _create_edited_yaml(base_yaml, edited_yaml, pattern, replacement):
    with open(base_yaml) as fd:
        content = fd.read()
        new_content = re.sub(pattern, replacement, content)
        with open(edited_yaml, "w") as fd:
            fd.write(new_content)


def _initialize_test(tmpdir, version):
    asdf_base = os.path.join(tmpdir, "base.asdf")
    yaml_base = os.path.join(tmpdir, "base.yaml")
    asdf_edit = os.path.join(tmpdir, "edit.asdf")
    yaml_edit = os.path.join(tmpdir, "edit.yaml")

    _create_base_asdf(version,asdf_base)
    shutil.copyfile(asdf_base, asdf_edit)

    args = ["edit", "-e", "-f", f"{asdf_base}", "-o", f"{yaml_base}"]
    main.main_from_args(args)

    return asdf_base, yaml_base, asdf_edit, yaml_edit


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_smaller(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(tmpdir, version)

    _create_edited_yaml(yaml_base, yaml_edit, "foo: 42", "foo: 2")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    ret = main.main_from_args(args)
    assert 0==ret

    with asdf.open(asdf_edit) as af:
        assert af.tree["foo"] == 2
        assert os.path.getsize(asdf_edit) == os.path.getsize(asdf_base)

@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_equal(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(tmpdir, version)

    _create_edited_yaml(yaml_base, yaml_edit, "foo: 42", "foo: 41")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    ret = main.main_from_args(args)
    assert 0==ret

    with asdf.open(asdf_edit) as af:
        assert af.tree["foo"] == 41
        assert os.path.getsize(asdf_edit) == os.path.getsize(asdf_base)

@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_larger(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(tmpdir, version)

    _create_edited_yaml(yaml_base, yaml_edit, "foo: 42", "foo: 41\nbar: 13")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    ret = main.main_from_args(args)
    assert 0==ret

    with asdf.open(asdf_edit) as af:
        assert "bar" in af.tree
        assert os.path.getsize(asdf_edit) - os.path.getsize(asdf_base) > 10000
