# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import copy
import io
import os

import numpy as np
from numpy.testing import assert_array_equal

from astropy.tests.helper import pytest

from ... import asdf
from ... import generic_io
from ...tests import helpers


def _get_large_tree():
    np.random.seed(0)
    x = np.random.rand(128, 128)
    tree = {
        'science_data': x,
        }
    return tree


def _get_sparse_tree():
    np.random.seed(0)
    arr = np.zeros((128, 128))
    for x, y, z in np.random.rand(64, 3):
        arr[int(x*127), int(y*127)] = z
    arr[0, 0] = 5.0
    tree = {'science_data': arr}
    return tree


def _roundtrip(tmpdir, tree, encoding=[],
               write_options={}, read_options={}):
    tmpfile = os.path.join(str(tmpdir), 'test.asdf')

    with asdf.AsdfFile(tree) as ff:
        ff.set_array_encoding(tree['science_data'], encoding)
        ff.write_to(tmpfile, **write_options)

    with asdf.AsdfFile().read(tmpfile, **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    # Also test saving to a buffer
    buff = io.BytesIO()

    with asdf.AsdfFile(tree) as ff:
        ff.set_array_encoding(tree['science_data'], encoding)
        ff.write_to(buff, **write_options)

    buff.seek(0)
    with asdf.AsdfFile().read(buff, **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    # Test saving to a non-seekable buffer

    buff = io.BytesIO()

    with asdf.AsdfFile(tree) as ff:
        ff.set_array_encoding(tree['science_data'], encoding)
        ff.write_to(generic_io.OutputStream(buff), **write_options)

    buff.seek(0)
    with asdf.AsdfFile().read(generic_io.InputStream(buff), **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    return ff


def test_invalid_encoding():
    tree = _get_large_tree()
    ff = asdf.AsdfFile(tree)
    with pytest.raises(ValueError):
        ff.set_array_encoding(tree['science_data'], ['foo'])

    with pytest.raises(ValueError):
        ff.set_array_encoding(tree['science_data'], ['zlib', 'sparse'])

    ff.set_array_storage(tree['science_data'], 'streamed')
    with pytest.raises(ValueError):
        ff.set_array_encoding(tree['science_data'], ['zlib'])


def test_zlib(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, 'zlib')


def test_double_zlib(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, ['zlib', 'zlib'])


def test_triple_zlib(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, ['zlib', 'zlib', 'zlib'])


def test_update_zlib(tmpdir):
    tree = _get_sparse_tree()
    tree['science_data2'] = copy.copy(tree['science_data'])

    tmpfile = os.path.join(str(tmpdir), 'test.asdf')

    with asdf.AsdfFile(tree) as ff:
        ff.set_array_encoding(tree['science_data'], ['zlib'])
        ff.write_to(tmpfile)
        ff.tree['science_data'] += 2
        ff.update()

    with asdf.AsdfFile().read(tmpfile) as ff:
        assert_array_equal(tree['science_data'], ff.tree['science_data'])
        assert_array_equal(tree['science_data2'], ff.tree['science_data2'])


def test_tiling(tmpdir):
    tree = _get_sparse_tree()

    _roundtrip(tmpdir, tree, [('tile', {'shape': (2, 2)})])


def test_tiling_zlib(tmpdir):
    tree = _get_sparse_tree()

    _roundtrip(tmpdir, tree, [('tile', {'shape': (8, 8)}), 'zlib'])
