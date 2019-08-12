# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import io
import os
import sys

import pytest

import urllib.request as urllib_request

import numpy as np

import asdf
from asdf import util
from asdf import generic_io
from asdf.asdf import is_asdf_file

from . import helpers, create_small_tree, create_large_tree


@pytest.fixture(params=[create_small_tree, create_large_tree])
def tree(request):
    return request.param()


def _roundtrip(tree, get_write_fd, get_read_fd,
               write_options={}, read_options={}):

    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    write_options.setdefault('all_array_storage', 'internal')

    with get_write_fd() as fd:
        asdf.AsdfFile(tree).write_to(fd, **write_options)
        # Work around the fact that generic_io's get_file doesn't have a way of
        # determining whether or not the underlying file handle should be
        # closed as part of the exit handler
        if isinstance(fd._fd, io.FileIO):
            fd._fd.close()

    with get_read_fd() as fd:
        ff = asdf.open(fd, **read_options)
        helpers.assert_tree_match(tree, ff.tree)

    return ff


def test_mode_fail(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    with pytest.raises(ValueError):
        generic_io.get_file(path, mode="r+")


def test_open(tmpdir, small_tree):
    from .. import open

    path = os.path.join(str(tmpdir), 'test.asdf')

    # Simply tests the high-level "open" function
    ff = asdf.AsdfFile(small_tree)
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
        # Must open with mode=rw in order to get memmapped data
        f = generic_io.get_file(path, mode='rw')
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
        f = generic_io.get_file(open(path, 'wb'), mode='w', close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        return f

    def get_read_fd():
        # Must open with mode=rw in order to get memmapped data
        f = generic_io.get_file(open(path, 'r+b'), mode='rw', close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
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


def test_io_open(tree, tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    def get_write_fd():
        f = generic_io.get_file(io.open(path, 'wb'), mode='w', close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        return f

    def get_read_fd():
        f = generic_io.get_file(io.open(path, 'r+b'), mode='rw', close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == util.filepath_to_url(path)
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(list(ff.blocks.internal_blocks)) == 2
        assert isinstance(next(ff.blocks.internal_blocks)._data, np.core.memmap)
        ff.tree['science_data'][0] = 42


def test_close_underlying(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    with generic_io.get_file(open(path, 'wb'), mode='w', close=True) as ff:
        pass

    assert ff.is_closed() == True
    assert ff._fd.closed == True

    with generic_io.get_file(open(path, 'rb'), close=True) as ff2:
        pass

    assert ff2.is_closed() == True
    assert ff2._fd.closed == True


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


@pytest.mark.remote_data
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


@pytest.mark.remote_data
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


@pytest.mark.remote_data
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
        with asdf.open(fd) as ff:
            with pytest.raises(ValueError):
                helpers.assert_tree_match(tree, ff.tree)


@pytest.mark.remote_data
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


def test_exploded_stream_write(small_tree):
    # Writing an exploded file to an output stream should fail, since
    # we can't write "files" alongside it.

    ff = asdf.AsdfFile(small_tree)

    with pytest.raises(ValueError):
        ff.write_to(io.BytesIO(), all_array_storage='external')


def test_exploded_stream_read(tmpdir, small_tree):
    # Reading from an exploded input file should fail, but only once
    # the data block is accessed.  This behavior is important so that
    # the tree can still be accessed even if the data is missing.

    path = os.path.join(str(tmpdir), 'test.asdf')

    ff = asdf.AsdfFile(small_tree)
    ff.write_to(path, all_array_storage='external')

    with open(path, 'rb') as fd:
        # This should work, so we can get the tree content
        x = generic_io.InputStream(fd, 'r')
        with asdf.open(x) as ff:
            # It's only when trying to access external data that an error occurs
            with pytest.raises(ValueError):
                ff.tree['science_data'][:]


def test_unicode_open(tmpdir, small_tree):
    path = os.path.join(str(tmpdir), 'test.asdf')

    ff = asdf.AsdfFile(small_tree)

    ff.write_to(path)

    with io.open(path, 'rt', encoding="utf-8") as fd:
        with pytest.raises(ValueError):
            with asdf.open(fd):
                pass


def test_invalid_obj(tmpdir):
    with pytest.raises(ValueError):
        generic_io.get_file(42)

    path = os.path.join(str(tmpdir), 'test.asdf')
    with generic_io.get_file(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, 'r')

    with pytest.raises(ValueError):
        generic_io.get_file("http://www.google.com", "w")

    with pytest.raises(TypeError):
        generic_io.get_file(io.StringIO())

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, 'w')

    with io.open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, 'w')

    with generic_io.get_file(sys.__stdout__, 'w'):
        pass


def test_nonseekable_file(tmpdir):
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
    class Wrapper:
        def __init__(self, init):
            self._fd = init

    class Random:
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


def test_truncated_reader():
    """
    Tests several edge cases for _TruncatedReader.read()

    Includes regression test for
    https://github.com/spacetelescope/asdf/pull/181
    """

    # TODO: Should probably break this up into multiple test cases

    fd = generic_io.RandomAccessFile(io.BytesIO(), 'rw')
    content = b'a' * 100 + b'b'
    fd.write(content)
    fd.seek(0)

    # Simple cases where the delimiter is not found at all
    tr = generic_io._TruncatedReader(fd, b'x', 1)
    with pytest.raises(ValueError):
        tr.read()

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'x', 1)
    assert tr.read(100) == content[:100]
    assert tr.read(1) == content[100:]
    with pytest.raises(ValueError):
        tr.read()

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'x', 1, exception=False)
    assert tr.read() == content

    # No delimiter but with 'initial_content'
    init = b'abcd'
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'x', 1, initial_content=init,
                                     exception=False)
    assert tr.read(100) == (init + content)[:100]
    assert tr.read() == (init + content)[100:]

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'x', 1, initial_content=init,
                                     exception=False)
    assert tr.read() == init + content

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'x', 1, initial_content=init,
                                     exception=False)
    assert tr.read(2) == init[:2]
    assert tr.read() == init[2:] + content

    # Some tests of a single character delimiter
    # Add some trailing data after the delimiter
    fd.seek(0, 2)
    fd.write(b'ffff')

    # Delimiter not included in read
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'b', 1)
    assert tr.read(100) == content[:100]
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'b', 1)
    assert tr.read() == content[:100]

    # Delimiter included
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'b', 1, include=True)
    assert tr.read() == content[:101]
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'b', 1, include=True)
    assert tr.read(101) == content[:101]
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'b', 1, include=True)
    assert tr.read(102) == content[:101]
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b'b', 1, include=True)
    assert tr.read(100) == content[:100]
    assert tr.read(1) == content[100:101]
    assert tr.read() == b''


    # Longer delimiter with variable length
    content = b'a' * 100 + b'\n...\n' + b'ffffff'
    delimiter = br'\r?\n\.\.\.((\r?\n)|$)'
    readahead = 7

    fd = generic_io.RandomAccessFile(io.BytesIO(), 'rw')
    fd.write(content)

    # Delimiter not included in read
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read() == content[:100]
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(100) == content[:100]
    assert tr.read() == b''

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(99) == content[:99]
    assert tr.read() == content[99:100]
    assert tr.read() == b''

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(99) == content[:99]
    assert tr.read(2) == content[99:100]
    assert tr.read() == b''

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(99) == content[:99]
    assert tr.read(50) == content[99:100]
    assert tr.read() == b''

    # Same as the previous set of tests, but including the delimiter
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read() == content[:105]
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(105) == content[:105]
    assert tr.read() == b''

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(99) == content[:99]
    assert tr.read() == content[99:105]
    assert tr.read() == b''

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(99) == content[:99]
    assert tr.read(2) == content[99:101]
    assert tr.read() == content[101:105]
    assert tr.read() == b''

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(99) == content[:99]
    assert tr.read(50) == content[99:105]
    assert tr.read() == b''

    # Same sequence of tests but with some 'initial_content'
    init = b'abcd'

    # Delimiter not included in read
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead,
                                     initial_content=init)
    assert tr.read() == (init + content[:100])
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead,
                                     initial_content=init)
    assert tr.read(100) == (init + content[:96])
    assert tr.read() == content[96:100]
    assert tr.read() == b''

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead,
                                     initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read() == content[95:100]
    assert tr.read() == b''

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead,
                                     initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(6) == content[95:100]
    assert tr.read() == b''

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead,
                                     initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(50) == content[95:100]
    assert tr.read() == b''

    # Same as the previous set of tests, but including the delimiter
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True,
                                     initial_content=init)
    assert tr.read() == (init + content[:105])
    assert tr.read() == b''

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True,
                                     initial_content=init)
    assert tr.read(105) == (init + content[:101])
    assert tr.read() == content[101:105]
    assert tr.read() == b''

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True,
                                     initial_content=init)
    assert tr.read(103) == (init + content[:99])
    assert tr.read() == content[99:105]
    assert tr.read() == b''

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True,
                                     initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(6) == content[95:101]
    assert tr.read() == content[101:105]
    assert tr.read() == b''

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True,
                                     initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(50) == content[95:105]
    assert tr.read() == b''


def test_is_asdf(tmpdir):
    # test fits
    fits = pytest.importorskip('astropy.io.fits')

    hdul = fits.HDUList()
    phdu= fits.PrimaryHDU()
    imhdu= fits.ImageHDU(data=np.arange(24).reshape((4,6)))
    hdul.append(phdu)
    hdul.append(imhdu)
    path = os.path.join(str(tmpdir), 'test.fits')
    hdul.writeto(path)
    assert not is_asdf_file(path)
    assert is_asdf_file(asdf.AsdfFile())
