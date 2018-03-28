# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import os
import sys
import pytest

from asdf import open as asdf_open
from asdf import versioning

from .helpers import assert_tree_match, display_warnings


def get_test_id(reference_file_path):
    """Helper function to return the informative part of a schema path"""
    path = os.path.normpath(reference_file_path)
    return os.path.sep.join(path.split(os.path.sep)[-3:])

def collect_reference_files():
    """Function used by pytest to collect ASDF reference files for testing."""
    root = os.path.join(os.path.dirname(__file__), '..', "reference_files")
    for version in versioning.supported_versions:
        version_dir = os.path.join(root, str(version))
        if os.path.exists(version_dir):
            for filename in os.listdir(version_dir):
                if filename.endswith(".asdf"):
                    filepath = os.path.join(version_dir, filename)
                    basename, _ = os.path.splitext(filepath)
                    if os.path.exists(basename + ".yaml"):
                        yield filepath

def _compare_trees(name_without_ext, expect_warnings=False):
    asdf_path = name_without_ext + ".asdf"
    yaml_path = name_without_ext + ".yaml"

    with asdf_open(asdf_path) as af_handle:
        af_handle.resolve_and_inline()

        with asdf_open(yaml_path) as ref:

            def _compare_func():
                assert_tree_match(af_handle.tree, ref.tree,
                    funcname='assert_allclose')

            if expect_warnings:
                # Make sure to only suppress warnings when they are expected.
                # However, there's still a chance of missing warnings that we
                # actually care about here.
                with pytest.warns(RuntimeWarning) as w:
                    _compare_func()
            else:
                _compare_func()

@pytest.mark.parametrize(
    'reference_file', collect_reference_files(), ids=get_test_id)
def test_reference_file(reference_file):
    basename = os.path.basename(reference_file)
    name_without_ext, _ = os.path.splitext(reference_file)

    known_fail = False
    expect_warnings = False

    if sys.maxunicode <= 65535:
        known_fail = known_fail or (basename in ('unicode_spp.asdf'))

    try:
        _compare_trees(name_without_ext, expect_warnings=expect_warnings)
    except:
        if known_fail:
            pytest.xfail()
        else:
            raise
