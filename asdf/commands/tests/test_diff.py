# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import os
import io
from functools import partial

import numpy as np
import pytest

from ... import AsdfFile
from ...tests import helpers

from .. import main, diff

from . import data as test_data
get_test_data_path = partial(helpers.get_test_data_path, module=test_data)


def _assert_diffs_equal(filenames, result_file, minimal=False):
    iostream = io.StringIO()

    file_paths = [get_test_data_path(name) for name in filenames]
    diff(file_paths, minimal=minimal, iostream=iostream)
    iostream.seek(0)

    result_path = get_test_data_path(result_file)
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
        diff([get_test_data_path(name) for name in filenames], False)

def test_diff_command():
    filenames = ['frames0.asdf', 'frames1.asdf']
    paths = [get_test_data_path(name) for name in filenames]

    assert main.main_from_args(['diff'] + paths) == 0
