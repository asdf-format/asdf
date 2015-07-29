# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

import numpy as np

import pytest

from .. import asdf
from .. import generic_io
from ..tests import helpers


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


def _roundtrip(tmpdir, tree, compression=None,
               write_options={}, read_options={}):
    tmpfile = os.path.join(str(tmpdir), 'test.asdf')

    ff = asdf.AsdfFile(tree)
    ff.set_array_compression(tree['science_data'], compression)
    ff.write_to(tmpfile, **write_options)

    with asdf.AsdfFile.open(tmpfile, mode="rw") as ff:
        ff.update(**write_options)

    with asdf.AsdfFile.open(tmpfile, **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    # Also test saving to a buffer
    buff = io.BytesIO()

    ff = asdf.AsdfFile(tree)
    ff.set_array_compression(tree['science_data'], compression)
    ff.write_to(buff, **write_options)

    buff.seek(0)
    with asdf.AsdfFile.open(buff, **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    # Test saving to a non-seekable buffer
    buff = io.BytesIO()

    ff = asdf.AsdfFile(tree)
    ff.set_array_compression(tree['science_data'], compression)
    ff.write_to(generic_io.OutputStream(buff), **write_options)

    buff.seek(0)
    with asdf.AsdfFile.open(generic_io.InputStream(buff), **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    return ff


def test_invalid_compression():
    tree = _get_large_tree()
    ff = asdf.AsdfFile(tree)
    with pytest.raises(ValueError):
        ff.set_array_compression(tree['science_data'], 'foo')


def test_zlib(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, 'zlib')


def test_bzp2(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, 'bzp2')
