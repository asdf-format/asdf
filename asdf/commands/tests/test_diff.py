# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import os
import io

import numpy as np
import pytest

from ... import AsdfFile
from .. import main, diff


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def _assert_diffs_equal(filenames, result_file, minimal=False):
    iostream = io.StringIO()

    file_paths = ["{}/{}".format(TEST_DATA_PATH, name) for name in filenames]
    diff(file_paths, minimal=minimal, iostream=iostream)
    iostream.seek(0)

    result_path = "{}/{}".format(TEST_DATA_PATH, result_file)
    with open(result_path, 'r') as handle:
        assert handle.read() == iostream.read()

def test_diff():
    filenames = ['frames0.asdf', 'frames1.asdf']
    result_file = 'frames.diff'
    _assert_diffs_equal(filenames, result_file, minimal=False)

def test_diff_minimal():
    filenames = ['frames0.asdf', 'frames1.asdf']
    result_file = 'frames_minimal.diff'
    _assert_diffs_equal(filenames, result_file, minimal=True)

def test_diff_block():
    filenames = ['block0.asdf', 'block1.asdf']
    result_file = 'blocks.diff'

    _assert_diffs_equal(filenames, result_file, minimal=False)

def test_file_not_found():
    # Try to open files that exist but are not valid asdf
    filenames = ['frames.diff', 'blocks.diff']
    with pytest.raises(RuntimeError):
        diff(["{}/{}".format(TEST_DATA_PATH, name) for name in filenames], False)

def test_diff_command():
    filenames = ['frames0.asdf', 'frames1.asdf']
    paths = ["{}/{}".format(TEST_DATA_PATH, name) for name in filenames]

    assert main.main_from_args(['diff'] + paths) == 0
