# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os
import sys

import pytest

import six
import six.moves.urllib.request as urllib_request

import numpy as np

from .. import asdf
from .. import generic_io
from .. import util

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
        asdf.AsdfFile(tree).write_to(fd, **write_options)

    with get_read_fd() as fd:
        ff = asdf.AsdfFile.open(fd, **read_options)
        helpers.assert_tree_match(tree, ff.tree)

    return ff


def test_mode_fail(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    with pytest.raises(ValueError):
        generic_io.get_file(path, mode="r+")


def test_open(tmpdir):
    from .. import open

    path = os.path.join(str(tmpdir), 'test.asdf')

    # Simply tests the high-level "open" function
    ff = asdf.AsdfFile(_get_small_tree())
    ff.write_to(path)
    with open(path) as ff2:
        helpers.assert_tree_match(ff2.tree, ff.tree)


def test_path(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    def get_write_fd():
        f = generic_io.get_file(path, mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        return f

    def get_read_fd():
        f = generic_io.get_file(path, mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        # This is to check for a "feature" in Python 3.x that reading zero
        # bytes from a socket causes it to stop.  We have code in generic_io.py
        # to workaround it.
        f.read(0)
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        next(ff.blocks.internal_blocks).data
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)


def test_open2(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    def get_write_fd():
        f = generic_io.get_file(open(path, 'wb'), mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        f._close = True
        return f

    def get_read_fd():
        f = generic_io.get_file(open(path, 'rb'), mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        f._close = True
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)


def test_open_fail(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    with open(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='w')


def test_open_fail2(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    with io.open(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='w')


if six.PY3:
    def test_open_fail3(tmpdir):
        path = os.path.join(str(tmpdir), 'test.asdf')

        with open(path, 'w') as fd:
            fd.write("\n\n\n")

        with open(path, 'r') as fd:
            with pytest.raises(ValueError):
                generic_io.get_file(fd, mode='r')


def test_open_fail4(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    with open(path, 'w') as fd:
        fd.write("\n\n\n")

    with io.open(path, 'r') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='r')


@pytest.mark.skipif(sys.version_info[:2] == (2, 6),
                    reason="requires python 2.7 or later")
def test_io_open(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    def get_write_fd():
        f = generic_io.get_file(io.open(path, 'wb'), mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        f._close = True
        return f

    def get_read_fd():
        f = generic_io.get_file(io.open(path, 'r+b'), mode='rw')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        f._close = True
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        ff.tree['science_data'][0] = 42


def test_bytes_io(tree):
    buff = io.BytesIO()

    def get_write_fd():
        f = generic_io.get_file(buff, mode='w')
        assert isinstance(f, generic_io.MemoryIO)
        return f

    def get_read_fd():
        buff.seek(0)
        f = generic_io.get_file(buff, mode='rw')
        assert isinstance(f, generic_io.MemoryIO)
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        assert not isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.ndarray)
        ff.tree['science_data'][0] = 42


def test_streams(tree):
    buff = io.BytesIO()

    def get_write_fd():
        return generic_io.OutputStream(buff)

    def get_read_fd():
        buff.seek(0)
        return generic_io.InputStream(buff, 'rw')

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(ff.blocks) == 2
        assert not isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.ndarray)
        ff.tree['science_data'][0] = 42


def test_streams2():
    buff = io.BytesIO(b'\0' * 60)
    buff.seek(0)

    fd = generic_io.InputStream(buff, 'r')

    x = fd._peek(10)
    x = fd.read()
    assert len(x) == 60


@pytest.mark.skipif(sys.platform.startswith('win'),
                    reason="Windows firewall prevents test")
def test_urlopen(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, 'test.asdf')

    def get_write_fd():
        return generic_io.get_file(open(path, 'wb'), mode='w')

    def get_read_fd():
        return generic_io.get_file(
            urllib_request.urlopen(
                httpserver.url + "test.asdf"))

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        assert not isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.ndarray)


@pytest.mark.skipif(sys.platform.startswith('win'),
                    reason="Windows firewall prevents test")
def test_http_connection(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, 'test.asdf')

    def get_write_fd():
        return generic_io.get_file(open(path, 'wb'), mode='w')

    def get_read_fd():
        fd = generic_io.get_file(httpserver.url + "test.asdf")
        assert isinstance(fd, generic_io.InputStream)
        # This is to check for a "feature" in Python 3.x that reading zero
        # bytes from a socket causes it to stop.  We have code in generic_io.py
        # to workaround it.
        fd.read(0)
        return fd

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        assert not isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.ndarray)
        ff.tree['science_data'][0] == 42


@pytest.mark.skipif(sys.platform.startswith('win'),
                    reason="Windows firewall prevents test")
def test_http_connection_range(tree, rhttpserver):
    path = os.path.join(rhttpserver.tmpdir, 'test.asdf')
    connection = [None]

    def get_write_fd():
        return generic_io.get_file(open(path, 'wb'), mode='w')

    def get_read_fd():
        fd = generic_io.get_file(rhttpserver.url + "test.asdf")
        assert isinstance(fd, generic_io.HTTPConnection)
        connection[0] = fd
        return fd

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        if len(tree) == 4:
            assert connection[0]._nreads == 0
        else:
            assert connection[0]._nreads == 6

        assert len(list(ff.blocks.internal_blocks)) == 2
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.ndarray)
        ff.tree['science_data'][0] == 42


def test_exploded_filesystem(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    def get_write_fd():
        return generic_io.get_file(path, mode='w')

    def get_read_fd():
        return generic_io.get_file(path, mode='r')

    with _roundtrip(tree, get_write_fd, get_read_fd,
                    write_options={'all_array_storage': 'external'}) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 0
        assert len(list(ff.blocks.external_blocks)) == 2


def test_exploded_filesystem_fail(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    def get_write_fd():
        return generic_io.get_file(path, mode='w')

    def get_read_fd():
        fd = io.BytesIO()
        with open(path, mode='rb') as fd2:
            fd.write(fd2.read())
        fd.seek(0)
        return fd

    with get_write_fd() as fd:
        asdf.AsdfFile(tree).write_to(fd, all_array_storage='external')

    with get_read_fd() as fd:
        with asdf.AsdfFile.open(fd) as ff:
            with pytest.raises(ValueError):
                helpers.assert_tree_match(tree, ff.tree)


@pytest.mark.skipif(sys.platform.startswith('win'),
                    reason="Windows firewall prevents test")
def test_exploded_http(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, 'test.asdf')

    def get_write_fd():
        return generic_io.get_file(path, mode='w')

    def get_read_fd():
        return generic_io.get_file(httpserver.url + "test.asdf")

    with _roundtrip(tree, get_write_fd, get_read_fd,
                    write_options={'all_array_storage': 'external'}) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 0
        assert len(list(ff.blocks.external_blocks)) == 2


def test_exploded_stream_write():
    # Writing an exploded file to an output stream should fail, since
    # we can't write "files" alongside it.

    tree = _get_small_tree()

    ff = asdf.AsdfFile(tree)

    with pytest.raises(ValueError):
        ff.write_to(io.BytesIO(), all_array_storage='external')


def test_exploded_stream_read(tmpdir):
    # Reading from an exploded input file should fail, but only once
    # the data block is accessed.  This behavior is important so that
    # the tree can still be accessed even if the data is missing.
    tree = _get_small_tree()

    path = os.path.join(str(tmpdir), 'test.asdf')

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, all_array_storage='external')

    with open(path, 'rb') as fd:
        # This should work, so we can get the tree content
        x = generic_io.InputStream(fd, 'r')
        with asdf.AsdfFile.open(x) as ff:
            pass

    # It's only on trying to get at the block data that the error
    # occurs.
    with pytest.raises(ValueError):
        ff.tree['science_data'][:]


def test_unicode_open(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    tree = _get_small_tree()
    ff = asdf.AsdfFile(tree)

    ff.write_to(path)

    with io.open(path, 'rt', encoding="utf-8") as fd:
        with pytest.raises(ValueError):
            with asdf.AsdfFile.open(fd):
                pass


def test_invalid_obj(tmpdir):
    with pytest.raises(ValueError):
        generic_io.get_file(42)

    path = os.path.join(str(tmpdir), 'test.asdf')
    with generic_io.get_file(path, 'w') as fd:
        with pytest.raises(ValueError):
            fd2 = generic_io.get_file(fd, 'r')

    with pytest.raises(ValueError):
        fd2 = generic_io.get_file("http://www.google.com", "w")

    with pytest.raises(TypeError):
        fd2 = generic_io.get_file(io.StringIO())

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            fd2 = generic_io.get_file(fd, 'w')

    with io.open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            fd2 = generic_io.get_file(fd, 'w')

    with generic_io.get_file(sys.__stdout__, 'w'):
        pass


def test_nonseekable_file(tmpdir):
    if six.PY2:
        base = file
    else:
        base = io.IOBase

    class FileWrapper(base):
        def tell(self):
            raise IOError()

        def seekable(self):
            return False

        def readable(self):
            return True

        def writable(self):
            return True

    with FileWrapper(os.path.join(str(tmpdir), 'test.asdf'), 'wb') as fd:
        assert isinstance(generic_io.get_file(fd, 'w'), generic_io.OutputStream)
        with pytest.raises(ValueError):
            generic_io.get_file(fd, 'rw')

    with FileWrapper(os.path.join(str(tmpdir), 'test.asdf'), 'rb') as fd:
        assert isinstance(generic_io.get_file(fd, 'r'), generic_io.InputStream)


def test_relative_uri():
    assert generic_io.relative_uri(
        'http://www.google.com', 'file://local') == 'file://local'


def test_arbitrary_file_object():
    class Wrapper(object):
        def __init__(self, init):
            self._fd = init

    class Random(object):
        def seek(self, *args):
            return self._fd.seek(*args)

        def tell(self, *args):
            return self._fd.tell(*args)

    class Reader(Wrapper):
        def read(self, *args):
            return self._fd.read(*args)

    class RandomReader(Reader, Random):
        pass

    class Writer(Wrapper):
        def write(self, *args):
            return self._fd.write(*args)

    class RandomWriter(Writer, Random):
        pass

    class All(Reader, Writer, Random):
        pass

    buff = io.BytesIO()
    assert isinstance(
        generic_io.get_file(Reader(buff), 'r'), generic_io.InputStream)
    assert isinstance(
        generic_io.get_file(Writer(buff), 'w'), generic_io.OutputStream)
    assert isinstance(
        generic_io.get_file(RandomReader(buff), 'r'), generic_io.MemoryIO)
    assert isinstance(
        generic_io.get_file(RandomWriter(buff), 'w'), generic_io.MemoryIO)
    assert isinstance(
        generic_io.get_file(All(buff), 'rw'), generic_io.MemoryIO)
    assert isinstance(
        generic_io.get_file(All(buff), 'r'), generic_io.MemoryIO)
    assert isinstance(
        generic_io.get_file(All(buff), 'w'), generic_io.MemoryIO)

    with pytest.raises(ValueError):
        generic_io.get_file(Reader(buff), 'w')

    with pytest.raises(ValueError):
        generic_io.get_file(Writer(buff), 'r')


def test_check_bytes(tmpdir):
    with io.open(os.path.join(str(tmpdir), 'test.asdf'), 'w', encoding='utf-8') as fd:
        assert generic_io._check_bytes(fd, 'r') is False
        assert generic_io._check_bytes(fd, 'rw') is False
        assert generic_io._check_bytes(fd, 'w') is False

    with io.open(os.path.join(str(tmpdir), 'test.asdf'), 'wb') as fd:
        assert generic_io._check_bytes(fd, 'r') is True
        assert generic_io._check_bytes(fd, 'rw') is True
        assert generic_io._check_bytes(fd, 'w') is True
