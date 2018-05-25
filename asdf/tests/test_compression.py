# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io
import os

import numpy as np

import pytest

import asdf
from asdf import compression
from asdf import generic_io

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
    with pytest.raises(ValueError):
        compression._get_decoder('foo')
    with pytest.raises(ValueError):
        compression._get_encoder('foo')


def test_get_compressed_size():
    assert compression.get_compressed_size(b'0' * 1024, 'zlib') < 1024


def test_decompress_too_long_short():
    fio = io.BytesIO()
    compression.compress(fio, b'0' * 1024, 'zlib')
    size = fio.tell()
    fio.seek(0)
    fio.read_blocks = lambda us: [fio.read(us)]
    compression.decompress(fio, size, 1024, 'zlib')
    fio.seek(0)
    with pytest.raises(ValueError):
        compression.decompress(fio, size, 1025, 'zlib')
    fio.seek(0)
    with pytest.raises(ValueError):
        compression.decompress(fio, size, 1023, 'zlib')


def test_zlib(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, 'zlib')


def test_bzp2(tmpdir):
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, 'bzp2')

    
def test_lz4(tmpdir):
    pytest.importorskip('lz4')
    tree = _get_large_tree()

    _roundtrip(tmpdir, tree, 'lz4')


def test_recompression(tmpdir):
    tree = _get_large_tree()
    tmpfile = os.path.join(str(tmpdir), 'test1.asdf')
    afile = asdf.AsdfFile(tree)
    afile.write_to(tmpfile, all_array_compression='zlib')
    afile.close()
    afile = asdf.AsdfFile.open(tmpfile)
    tmpfile = os.path.join(str(tmpdir), 'test2.asdf')
    afile.write_to(tmpfile, all_array_compression='bzp2')
    afile.close()
    afile = asdf.AsdfFile.open(tmpfile)
    helpers.assert_tree_match(tree, afile.tree)
    afile.close()


def test_input(tmpdir):
    tree = _get_large_tree()
    tmpfile = os.path.join(str(tmpdir), 'test1.asdf')
    afile = asdf.AsdfFile(tree)
    afile.write_to(tmpfile, all_array_compression='zlib')
    afile.close()
    afile = asdf.AsdfFile.open(tmpfile)
    tmpfile = os.path.join(str(tmpdir), 'test2.asdf')
    afile.write_to(tmpfile)
    afile.close()
    afile = asdf.AsdfFile.open(tmpfile)
    helpers.assert_tree_match(tree, afile.tree)
    assert afile.get_array_compression(afile.tree['science_data']) == 'zlib'
    afile.close()


def test_none(tmpdir):

    tree = _get_large_tree()

    tmpfile1 = os.path.join(str(tmpdir), 'test1.asdf')
    with asdf.AsdfFile(tree) as afile:
        afile.write_to(tmpfile1)

    tmpfile2 = os.path.join(str(tmpdir), 'test2.asdf')
    with asdf.AsdfFile.open(tmpfile1) as afile:
        assert afile.get_array_compression(afile.tree['science_data']) is None
        afile.write_to(tmpfile2, all_array_compression='zlib')
        assert afile.get_array_compression(afile.tree['science_data']) == 'zlib'

    with asdf.AsdfFile.open(tmpfile2) as afile:
        afile.write_to(tmpfile1, all_array_compression=None)

    with asdf.AsdfFile.open(tmpfile1) as afile:
        helpers.assert_tree_match(tree, afile.tree)
        assert afile.get_array_compression(afile.tree['science_data']) is None


def test_set_array_compression(tmpdir):

    tmpfile = os.path.join(str(tmpdir), 'compressed.asdf')

    zlib_data = np.array([x for x in range(1000)])
    bzp2_data = np.array([x for x in range(1000)])

    tree = dict(zlib_data=zlib_data, bzp2_data=bzp2_data)
    with asdf.AsdfFile(tree) as af_out:
        af_out.set_array_compression(zlib_data, 'zlib')
        af_out.set_array_compression(bzp2_data, 'bzp2')
        af_out.write_to(tmpfile)

    with asdf.open(tmpfile) as af_in:
        assert af_in.get_array_compression(af_in.tree['zlib_data']) == 'zlib'
        assert af_in.get_array_compression(af_in.tree['bzp2_data']) == 'bzp2'
