# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import os

import numpy as np

import asdf
from asdf import AsdfFile
from asdf.commands import main
from ...tests.helpers import get_file_sizes, assert_tree_match


def test_explode_then_implode(tmpdir):
    x = np.arange(0, 10, dtype=np.float)

    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2],
        'not_shared': np.arange(10, 0, -1, dtype=np.uint8)
        }

    path = os.path.join(str(tmpdir), 'original.asdf')
    ff = AsdfFile(tree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ff.write_to(path, all_array_storage='internal')
    assert len(ff.blocks) == 2

    result = main.main_from_args(['explode', path])

    assert result == 0

    files = get_file_sizes(str(tmpdir))

    assert 'original.asdf' in files
    assert 'original_exploded.asdf' in files
    assert 'original_exploded0000.asdf' in files
    assert 'original_exploded0001.asdf' in files
    assert 'original_exploded0002.asdf' not in files

    assert files['original.asdf'] > files['original_exploded.asdf']

    path = os.path.join(str(tmpdir), 'original_exploded.asdf')
    result = main.main_from_args(['implode', path])

    assert result == 0

    with asdf.open(str(tmpdir.join('original_exploded_all.asdf'))) as af:
        assert_tree_match(af.tree, tree)
        assert len(af.blocks) == 2


def test_file_not_found(tmpdir):
    path = os.path.join(str(tmpdir), 'original.asdf')
    assert main.main_from_args(['explode', path]) == 2
