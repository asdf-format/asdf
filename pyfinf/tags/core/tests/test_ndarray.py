# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import sys

from astropy.extern import six

import numpy as np
from numpy.testing import assert_array_equal

from ....tests import helpers
from .... import finf
from .... import yamlutil

from .. import ndarray


def test_sharing(tmpdir):
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }

    def check_finf(finf):
        tree = finf.tree

        assert_array_equal(tree['science_data'], x)
        assert_array_equal(tree['subset'], x[3:-3])
        assert_array_equal(tree['skipping'], x[::2])

        assert tree['science_data'].ctypes.data == tree['skipping'].ctypes.data

        assert len(list(finf.blocks.internal_blocks)) == 1
        assert next(finf.blocks.internal_blocks)._size == 80

        tree['science_data'][0] = 42
        assert tree['skipping'][0] == 42

    def check_raw_yaml(content):
        assert b'!core/ndarray' in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)


def test_byteorder(tmpdir):
    tree = {
        'bigendian': np.arange(0, 10, dtype=str('>f8')),
        'little': np.arange(0, 10, dtype=str('<f8')),
        }

    def check_finf(finf):
        tree = finf.tree

        if sys.byteorder == 'little':
            assert tree['bigendian'].dtype.byteorder == '>'
            assert tree['little'].dtype.byteorder == '='
        else:
            assert tree['bigendian'].dtype.byteorder == '='
            assert tree['little'].dtype.byteorder == '<'

    def check_raw_yaml(content):
        assert b'byteorder: little' in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)


def test_all_dtypes(tmpdir):
    tree = {}
    for byteorder in ('>', '<'):
        for dtype in ndarray._dtype_names.values():
            # Python 3 can't expose these dtypes in non-native byte
            # order, because it's using the new Python buffer
            # interface.
            if six.PY3 and dtype in ('c32', 'f16'):
                continue
            tree[byteorder + dtype] = np.arange(0, 10, dtype=str(byteorder + dtype))

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_dont_load_data():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }
    ff = finf.FinfFile(tree)

    buff = io.BytesIO()
    ff.write_to(buff)

    buff.seek(0)
    ff = finf.FinfFile.read(buff)

    ctx = yamlutil.Context(ff)
    ctx.run_hook(ff._tree, 'pre_write')

    # repr and str shouldn't load data
    str(ff.tree['science_data'])
    repr(ff.tree)

    for block in ff.blocks.internal_blocks:
        assert block._data is None


def test_inline():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }

    buff = io.BytesIO()

    with finf.FinfFile(tree) as ff:
        ff.blocks[tree['science_data']].block_type = 'inline'
        ff.write_to(buff)

    buff.seek(0)
    with finf.FinfFile.read(buff, mode='rw') as ff:
        helpers.assert_tree_match(tree, ff.tree)
        assert len(list(ff.blocks.internal_blocks)) == 0
        buff = io.BytesIO()
        ff.write_to(buff)

    assert b'[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]' in buff.getvalue()


def test_inline_bare():
    content = "arr: !core/ndarray [[1, 2, 3, 4], [5, 6, 7, 8]]"
    buff = helpers.yaml_to_finf(content)

    ff = finf.FinfFile.read(buff)

    assert_array_equal(ff.tree['arr'], [[1, 2, 3, 4], [5, 6, 7, 8]])
