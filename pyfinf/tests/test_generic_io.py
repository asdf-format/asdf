# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os
import sys

import astropy.extern.six.moves.urllib.request as urllib_request
from astropy.tests.helper import pytest

import numpy as np

from .. import finf
from .. import generic_io

from . import helpers


def _get_small_tree():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2],
        'not_shared': np.arange(10, 0, -1, dtype=np.uint8)
        }
    return tree


def _get_large_tree():
    # These are designed to be big enough so they don't fit in a
    # single block, but not so big that RAM/disk space for the tests
    # is enormous.
    x = np.random.rand(256, 256)
    y = np.random.rand(16, 16, 16)
    tree = {
        'science_data': x,
        'more': y
        }
    return tree


@pytest.fixture(params=[_get_small_tree, _get_large_tree])
def tree(request):
    return request.param()


def _roundtrip(tree, get_write_fd, get_read_fd,
               write_options={}, read_options={}):
    with get_write_fd() as fd:
        finf.FinfFile(tree).write_to(fd, **write_options)

    with get_read_fd() as fd:
        ff = finf.FinfFile.read(fd, **read_options)

        helpers.assert_tree_match(tree, ff.tree)

    return ff


def test_path(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        f = generic_io.get_file(path, mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    def get_read_fd():
        f = generic_io.get_file(path, mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks._internal_blocks) == 2
    ff.blocks._internal_blocks[0].data
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)


def test_open(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        f = generic_io.get_file(open(path, 'wb'), mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    def get_read_fd():
        f = generic_io.get_file(open(path, 'rb'), mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks._internal_blocks) == 2
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)


def test_open_fail(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    with open(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='w')


def test_open_fail2(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    with io.open(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='w')


@pytest.mark.skipif(sys.version_info[:2] == (2, 6),
                    reason="requires python 2.7 or later")
def test_io_open(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        f = generic_io.get_file(io.open(path, 'wb'), mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    def get_read_fd():
        f = generic_io.get_file(io.open(path, 'rb'), mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks._internal_blocks) == 2
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)


def test_bytes_io(tree):
    buff = io.BytesIO()

    def get_write_fd():
        f = generic_io.get_file(buff, mode='w')
        assert isinstance(f, generic_io.MemoryIO)
        return f

    def get_read_fd():
        buff.seek(0)
        f = generic_io.get_file(buff, mode='r')
        assert isinstance(f, generic_io.MemoryIO)
        return f

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks._internal_blocks) == 2
    assert not isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.ndarray)


def test_streams(tree):
    buff = io.BytesIO()

    def get_write_fd():
        return generic_io.OutputStream(buff)

    def get_read_fd():
        buff.seek(0)
        return generic_io.InputStream(buff)

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks) == 2
    assert not isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.ndarray)


def test_urlopen(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, 'test.finf')

    def get_write_fd():
        return generic_io.get_file(open(path, 'wb'), mode='w')

    def get_read_fd():
        return generic_io.get_file(
            urllib_request.urlopen(
                httpserver.url + "test.finf"))

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks._internal_blocks) == 2
    assert not isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.ndarray)


def test_http_connection(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, 'test.finf')

    def get_write_fd():
        return generic_io.get_file(open(path, 'wb'), mode='w')

    def get_read_fd():
        fd = generic_io.get_file(httpserver.url + "test.finf")
        assert isinstance(fd, generic_io.InputStream)
        return fd

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    assert len(ff.blocks._internal_blocks) == 2
    assert not isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.ndarray)


def test_http_connection_range(tree, rhttpserver):
    path = os.path.join(rhttpserver.tmpdir, 'test.finf')
    connection = [None]

    def get_write_fd():
        return generic_io.get_file(open(path, 'wb'), mode='w')

    def get_read_fd():
        fd = generic_io.get_file(rhttpserver.url + "test.finf")
        assert isinstance(fd, generic_io.HTTPConnection)
        connection[0] = fd
        return fd

    ff = _roundtrip(tree, get_write_fd, get_read_fd)

    if len(tree) == 4:
        assert connection[0]._nreads == 1
    else:
        assert connection[0]._nreads == 4

    assert len(ff.blocks._internal_blocks) == 2
    assert not isinstance(ff.blocks._internal_blocks[0]._data, np.core.memmap)
    assert isinstance(ff.blocks._internal_blocks[0]._data, np.ndarray)


def test_exploded_filesystem(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        return generic_io.get_file(path, mode='w')

    def get_read_fd():
        return generic_io.get_file(path, mode='r')

    ff = _roundtrip(tree, get_write_fd, get_read_fd,
                    write_options={'exploded': True})

    assert len(ff.blocks._internal_blocks) == 0
    assert len(ff.blocks._external_blocks) == 2


def test_exploded_http(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, 'test.finf')

    def get_write_fd():
        return generic_io.get_file(path, mode='w')

    def get_read_fd():
        return generic_io.get_file(httpserver.url + "test.finf")

    ff = _roundtrip(tree, get_write_fd, get_read_fd,
                    write_options={'exploded': True})

    assert len(ff.blocks._internal_blocks) == 0
    assert len(ff.blocks._external_blocks) == 2


def test_exploded_stream_write():
    # Writing an exploded file to an output stream should fail, since
    # we can't write "files" alongside it.

    tree = _get_small_tree()

    ff = finf.FinfFile(tree)

    with pytest.raises(ValueError):
        ff.write_to(io.BytesIO(), exploded=True)


def test_exploded_stream_read(tmpdir):
    # Reading from an exploded input file should fail, but only once
    # the data block is accessed.  This behavior is important so that
    # the tree can still be accessed even if the data is missing.
    tree = _get_small_tree()

    path = os.path.join(str(tmpdir), 'test.finf')

    ff = finf.FinfFile(tree)

    ff.write_to(path, exploded=True)

    with open(path, 'rb') as fd:
        # This should work, so we can get the tree content
        x = generic_io.InputStream(fd)
        ff = finf.FinfFile.read(x)

    # It's only on trying to get at the block data that the error
    # occurs.
    with pytest.raises(ValueError):
        ff.tree['science_data'][:]
