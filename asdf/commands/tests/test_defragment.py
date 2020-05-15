# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import os

import numpy as np
import pytest

import asdf
from asdf import AsdfFile
from asdf.commands import main
from asdf.tests.helpers import get_file_sizes, assert_tree_match


def _test_defragment(tmpdir, codec):
    x = np.arange(0, 1000, dtype=np.float)

    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2],
        'not_shared': np.arange(100, 0, -1, dtype=np.uint8)
        }

    path = os.path.join(str(tmpdir), 'original.asdf')
    out_path = os.path.join(str(tmpdir), 'original.defragment.asdf')
    ff = AsdfFile(tree)
    ff.write_to(path)
    assert len(ff.blocks) == 2

    result = main.main_from_args(
        ['defragment', path, '-o', out_path, '-c', codec])

    assert result == 0

    files = get_file_sizes(str(tmpdir))

    assert 'original.asdf' in files
    assert 'original.defragment.asdf' in files

    assert files['original.defragment.asdf'] < files['original.asdf']

    with asdf.open(os.path.join(str(tmpdir), 'original.defragment.asdf')) as ff:
        assert_tree_match(ff.tree, tree)
        assert len(list(ff.blocks.internal_blocks)) == 2


def test_defragment_zlib(tmpdir):
    _test_defragment(tmpdir, 'zlib')


def test_defragment_bzp2(tmpdir):
    _test_defragment(tmpdir, 'bzp2')


def test_defragment_lz4(tmpdir):
    pytest.importorskip('lz4')
    _test_defragment(tmpdir, 'lz4')
