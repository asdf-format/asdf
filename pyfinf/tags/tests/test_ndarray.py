# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import sys

from astropy.extern import six

import numpy as np
from numpy.testing import assert_array_equal

from ...tests import helpers
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

        assert len(finf._blocks) == 1
        assert finf._blocks[0]._size == 80

    def check_raw_yaml(content):
        assert b'!ndarray' in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)


def test_byteorder(tmpdir):
    tree = {
        'bigendian': np.arange(0, 10, dtype='>f8'),
        'little': np.arange(0, 10, dtype='<f8'),
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
            tree[byteorder + dtype] = np.arange(0, 10, dtype=byteorder + dtype)

    helpers.assert_roundtrip_tree(tree, tmpdir)
