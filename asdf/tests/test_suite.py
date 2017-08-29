# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os
import sys

from asdf import open as asdf_open
from asdf import versioning

from .helpers import assert_tree_match

import pytest


def test_reference_files():
    def test_reference_file(filename):
        basename = os.path.basename(filename)

        known_fail = False
        if sys.version_info[:2] == (2, 6):
            known_fail = (basename in ('complex.asdf', 'unicode_spp.asdf'))
        elif sys.version_info[:2] == (2, 7):
            known_fail = (basename in ('complex.asdf'))

        if sys.maxunicode <= 65535:
            known_fail = known_fail | (basename in ('unicode_spp.asdf'))

        try:
            with asdf_open(filename) as asdf:
                asdf.resolve_and_inline()

                with asdf_open(filename[:-4] + "yaml") as ref:
                    assert_tree_match(asdf.tree, ref.tree,
                                      funcname='assert_allclose')
        except:
            if known_fail:
                pytest.xfail()
            else:
                raise

    root = os.path.join(os.path.dirname(__file__), '..', "reference_files")
    for version in versioning.supported_versions:
        version_dir = os.path.join(root, str(version))
        if os.path.exists(version_dir):
            for filename in os.listdir(version_dir):
                if filename.endswith(".asdf"):
                    filepath = os.path.join(version_dir, filename)
                    basename, _ = os.path.splitext(filepath)
                    if os.path.exists(basename + ".yaml"):
                        yield test_reference_file, filepath
