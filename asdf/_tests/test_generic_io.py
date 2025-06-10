import io
import os
import re
import stat
import sys
import urllib.request as urllib_request
from contextlib import nullcontext

import numpy as np
import pytest

import asdf
from asdf import exceptions, generic_io
from asdf.config import config_context
from asdf.exceptions import AsdfDeprecationWarning

from . import _helpers as helpers


@pytest.fixture(params=[True, False])
def has_fsspec(request, monkeypatch):
    if request.param:
        yield True
    else:
        pytest.importorskip("fsspec")
        monkeypatch.setitem(sys.modules, "fsspec", None)
        yield False


@pytest.fixture()
def warn_no_fsspec(has_fsspec):
    if has_fsspec:
        yield nullcontext()
    else:
        yield pytest.warns(
            AsdfDeprecationWarning, match=r"Opening http urls without fsspec is deprecated. Please install fsspec"
        )


def _roundtrip(tree, get_write_fd, get_read_fd, write_options=None, read_options=None):
    write_options = {} if write_options is None else write_options
    read_options = {} if read_options is None else read_options

    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    write_options.setdefault("all_array_storage", "internal")

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


def test_mode_fail(tmp_path):
    path = os.path.join(str(tmp_path), "test.asdf")

    with pytest.raises(ValueError, match=r"mode must be 'r', 'w' or 'rw'"):
        generic_io.get_file(path, mode="r+")


@pytest.mark.parametrize("mode", ["r", "w", "rw"])
def test_missing_directory(tmp_path, mode):
    path = str(tmp_path / "missing" / "test.asdf")
    regex_path = re.escape(path.replace("\\", "\\\\"))
    with pytest.raises(FileNotFoundError, match=f".*: '{regex_path}'$"):
        generic_io.get_file(path, mode=mode)


@pytest.mark.skipif(sys.platform.startswith("win"), reason="paths with two leading slashes are valid on windows")
@pytest.mark.parametrize("mode", ["r", "w", "rw"])
def test_two_leading_slashes(mode):
    """
    Providing a path with two leading slashes '//' will be parsed
    by urllib as having a netloc (unhandled by generic_io) and
    an invalid path. This creates an unhelpful error message on
    write (related to a missing atomic write file) and should be
    cause beforehand and provided with a more helpful error message

    Regression test for issue:
    https://github.com/asdf-format/asdf/issues/1353
    """
    path = "//bad/two/slashes"
    with pytest.raises(ValueError, match="Invalid path"):
        generic_io.get_file(path, mode=mode)


def test_open(tmp_path, small_tree):
    from asdf import open

    path = os.path.join(str(tmp_path), "test.asdf")

    # Simply tests the high-level "open" function
    ff = asdf.AsdfFile(small_tree)
    ff.write_to(path)
    with open(path) as ff2:
        helpers.assert_tree_match(ff2.tree, ff.tree)


def test_path(tree, tmp_path):
    path = tmp_path / "test.asdf"

    def get_write_fd():
        f = generic_io.get_file(path, mode="w")
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path.as_uri()
        return f

    def get_read_fd():
        # Must open with mode=rw in order to get memmapped data
        f = generic_io.get_file(path, mode="rw")
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path.as_uri()
        # This is to check for a "feature" in Python 3.x that reading zero
        # bytes from a socket causes it to stop.  We have code in generic_io.py
        # to workaround it.
        f.read(0)
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd, read_options={"memmap": True}) as ff:
        assert len(ff._blocks.blocks) == 2
        assert isinstance(ff._blocks.blocks[0].cached_data, np.memmap)


def test_open2(tree, tmp_path):
    path = tmp_path / "test.asdf"

    def get_write_fd():
        # cannot use context manager here because it closes the file
        f = generic_io.get_file(open(path, "wb"), mode="w", close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path.as_uri()
        return f

    def get_read_fd():
        # Must open with mode=rw in order to get memmapped data
        # cannot use context manager here because it closes the file
        f = generic_io.get_file(open(path, "r+b"), mode="rw", close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path.as_uri()
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd, read_options={"memmap": True}) as ff:
        assert len(ff._blocks.blocks) == 2
        assert isinstance(ff._blocks.blocks[0].cached_data, np.memmap)


@pytest.mark.parametrize("mode", ["r", "w", "rw"])
def test_open_not_binary_fail(tmp_path, mode):
    path = tmp_path / "test.asdf"

    with open(path, "w") as fd:
        fd.write("\n\n\n")

    file_mode = mode if mode != "rw" else "r+"
    with (
        open(path, file_mode) as fd,
        pytest.raises(
            ValueError,
            match=r"File-like object must be opened in binary mode.",
        ),
    ):
        generic_io.get_file(fd, mode=mode)


def test_io_open(tree, tmp_path):
    path = tmp_path / "test.asdf"

    def get_write_fd():
        # cannot use context manager here because it closes the file
        f = generic_io.get_file(open(path, "wb"), mode="w", close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path.as_uri()
        return f

    def get_read_fd():
        # cannot use context manager here because it closes the file
        f = generic_io.get_file(open(path, "r+b"), mode="rw", close=True)
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path.as_uri()
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd, read_options={"memmap": True}) as ff:
        assert len(ff._blocks.blocks) == 2
        assert isinstance(ff._blocks.blocks[0].cached_data, np.memmap)
        ff.tree["science_data"][0] = 42


def test_close_underlying(tmp_path):
    path = os.path.join(str(tmp_path), "test.asdf")

    with generic_io.get_file(open(path, "wb"), mode="w", close=True) as ff:
        pass

    assert ff.is_closed() is True
    assert ff._fd.closed is True

    with generic_io.get_file(open(path, "rb"), close=True) as ff2:
        pass

    assert ff2.is_closed() is True
    assert ff2._fd.closed is True


def test_bytes_io(tree):
    buff = io.BytesIO()

    def get_write_fd():
        f = generic_io.get_file(buff, mode="w")
        assert isinstance(f, generic_io.MemoryIO)
        return f

    def get_read_fd():
        buff.seek(0)
        f = generic_io.get_file(buff, mode="rw")
        assert isinstance(f, generic_io.MemoryIO)
        return f

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(ff._blocks.blocks) == 2
        assert not isinstance(ff._blocks.blocks[0].cached_data, np.memmap)
        ff.tree["science_data"][0] = 42


def test_streams(tree):
    buff = io.BytesIO()

    def get_write_fd():
        return generic_io.OutputStream(buff)

    def get_read_fd():
        buff.seek(0)
        return generic_io.InputStream(buff, "rw")

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(ff._blocks.blocks) == 2
        assert not isinstance(ff._blocks.blocks[0].cached_data, np.memmap)
        ff.tree["science_data"][0] = 42


def test_streams2():
    buff = io.BytesIO(b"\0" * 60)
    buff.seek(0)

    fd = generic_io.InputStream(buff, "r")

    x = fd.peek(10)
    x = fd.read()
    assert len(x) == 60


@pytest.mark.remote_data()
def test_urlopen(tree, httpserver):
    path = os.path.join(httpserver.tmpdir, "test.asdf")

    def get_write_fd():
        # cannot use context manager here because it closes the file
        return generic_io.get_file(open(path, "wb"), mode="w")

    def get_read_fd():
        return generic_io.get_file(urllib_request.urlopen(httpserver.url + "test.asdf"))

    with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
        assert len(ff._blocks.blocks) == 2
        assert not isinstance(ff._blocks.blocks[0].cached_data, np.memmap)


@pytest.mark.remote_data()
def test_http_connection(tree, httpserver, warn_no_fsspec):
    path = os.path.join(httpserver.tmpdir, "test.asdf")

    def get_write_fd():
        # cannot use context manager here because it closes the file
        return generic_io.get_file(open(path, "wb"), mode="w")

    def get_read_fd():
        fd = generic_io.get_file(httpserver.url + "test.asdf")
        # This is to check for a "feature" in Python 3.x that reading zero
        # bytes from a socket causes it to stop.  We have code in generic_io.py
        # to workaround it.
        fd.read(0)
        return fd

    with warn_no_fsspec:
        with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
            assert len(ff._blocks.blocks) == 2
            assert (ff.tree["science_data"] == tree["science_data"]).all()


def test_exploded_filesystem(tree, tmp_path):
    path = os.path.join(str(tmp_path), "test.asdf")

    def get_write_fd():
        return generic_io.get_file(path, mode="w")

    def get_read_fd():
        return generic_io.get_file(path, mode="r")

    with _roundtrip(tree, get_write_fd, get_read_fd, write_options={"all_array_storage": "external"}) as ff:
        assert len(ff._blocks.blocks) == 0


def test_exploded_filesystem_fail(tree, tmp_path):
    path = os.path.join(str(tmp_path), "test.asdf")

    def get_write_fd():
        return generic_io.get_file(path, mode="w")

    def get_read_fd():
        fd = io.BytesIO()
        with open(path, mode="rb") as fd2:
            fd.write(fd2.read())
        fd.seek(0)
        return fd

    with get_write_fd() as fd:
        asdf.AsdfFile(tree).write_to(fd, all_array_storage="external")

    with get_read_fd() as fd, asdf.open(fd) as ff, pytest.raises(ValueError, match=r"Resolved to relative URL"):
        helpers.assert_tree_match(tree, ff.tree)


@pytest.mark.remote_data()
def test_exploded_http(tree, httpserver, warn_no_fsspec):
    path = os.path.join(httpserver.tmpdir, "test.asdf")

    def get_write_fd():
        return generic_io.get_file(path, mode="w")

    def get_read_fd():
        return generic_io.get_file(httpserver.url + "test.asdf")

    with warn_no_fsspec:
        with _roundtrip(tree, get_write_fd, get_read_fd, write_options={"all_array_storage": "external"}) as ff:
            assert len(list(ff._blocks.blocks)) == 0


def test_exploded_stream_write(small_tree):
    # Writing an exploded file to an output stream should fail, since
    # we can't write "files" alongside it.

    ff = asdf.AsdfFile(small_tree)

    with pytest.raises(ValueError, match=r"Can't write external blocks, since URI of main file is unknown."):
        ff.write_to(io.BytesIO(), all_array_storage="external")


def test_exploded_stream_read(tmp_path, small_tree):
    # Reading from an exploded input file should fail, but only once
    # the data block is accessed.  This behavior is important so that
    # the tree can still be accessed even if the data is missing.

    path = os.path.join(str(tmp_path), "test.asdf")

    ff = asdf.AsdfFile(small_tree)
    ff.write_to(path, all_array_storage="external")

    with open(path, "rb") as fd:
        # This should work, so we can get the tree content
        x = generic_io.InputStream(fd, "r")
        # It's only when trying to access external data that an error occurs
        with asdf.open(x) as ff, pytest.raises(ValueError, match=r"Resolved to relative URL"):
            ff.tree["science_data"][:]


def test_unicode_open(tmp_path, small_tree):
    path = os.path.join(str(tmp_path), "test.asdf")

    ff = asdf.AsdfFile(small_tree)

    ff.write_to(path)

    with (
        open(path, encoding="utf-8") as fd,
        pytest.raises(
            ValueError,
            match=r"File-like object must be opened in binary mode.",
        ),
        asdf.open(fd),
    ):
        pass


def test_open_stdout():
    """Test ability to open/write stdout as an output stream"""
    with generic_io.get_file(sys.__stdout__, "w", close=True):
        pass


def test_invalid_obj(tmp_path, has_fsspec):
    with pytest.raises(ValueError, match=r"Can't handle .* as a file for mode 'r'"):
        generic_io.get_file(42)

    path = os.path.join(str(tmp_path), "test.asdf")
    with (
        generic_io.get_file(path, "w") as fd,
        pytest.raises(
            ValueError,
            match=r"File is opened as 'w', but 'r' was requested",
        ),
    ):
        generic_io.get_file(fd, "r")

    url = "http://www.google.com"
    mode = "w"
    if has_fsspec:
        raises_ctx = pytest.raises(ValueError, match=f"Unable to open {url} with mode {mode}")
    else:
        raises_ctx = pytest.raises(ValueError, match=r"HTTP connections can not be opened for writing")
    with raises_ctx:
        generic_io.get_file(url, mode)

    with pytest.raises(TypeError, match=r"io.StringIO objects are not supported.  Use io.BytesIO instead."):
        generic_io.get_file(io.StringIO())

    with open(path, "rb") as fd, pytest.raises(ValueError, match=r"File is opened as 'rb', but 'w' was requested"):
        generic_io.get_file(fd, "w")


def test_nonseekable_file(tmp_path):
    base = io.FileIO

    class FileWrapper(base):
        def tell(self):
            raise OSError

        def seekable(self):
            return False

        def readable(self):
            return True

        def writable(self):
            return True

    with FileWrapper(os.path.join(str(tmp_path), "test.asdf"), "wb") as fd:
        assert isinstance(generic_io.get_file(fd, "w"), generic_io.OutputStream)
        with pytest.raises(ValueError, match=r"File .* could not be opened in 'rw' mode"):
            generic_io.get_file(fd, "rw")

    with FileWrapper(os.path.join(str(tmp_path), "test.asdf"), "rb") as fd:
        assert isinstance(generic_io.get_file(fd, "r"), generic_io.InputStream)


def test_relative_uri():
    assert generic_io.relative_uri("http://www.google.com", "file://local") == "file://local"


@pytest.mark.parametrize("protocol", ["http", "asdf"])
def test_resolve_uri(protocol):
    """
    Confirm that the patched urllib.parse is handling
    asdf:// URIs correctly.
    """
    assert (
        generic_io.resolve_uri(f"{protocol}://somewhere.org/some-schema", "#/definitions/foo")
        == f"{protocol}://somewhere.org/some-schema#/definitions/foo"
    )

    assert (
        generic_io.resolve_uri(
            f"{protocol}://somewhere.org/path/to/some-schema",
            "../../some/other/path/to/some-other-schema",
        )
        == f"{protocol}://somewhere.org/some/other/path/to/some-other-schema"
    )


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
    assert isinstance(generic_io.get_file(Reader(buff), "r"), generic_io.InputStream)
    assert isinstance(generic_io.get_file(Writer(buff), "w"), generic_io.OutputStream)
    assert isinstance(generic_io.get_file(RandomReader(buff), "r"), generic_io.MemoryIO)
    assert isinstance(generic_io.get_file(RandomWriter(buff), "w"), generic_io.MemoryIO)
    assert isinstance(generic_io.get_file(All(buff), "rw"), generic_io.MemoryIO)
    assert isinstance(generic_io.get_file(All(buff), "r"), generic_io.MemoryIO)
    assert isinstance(generic_io.get_file(All(buff), "w"), generic_io.MemoryIO)

    with pytest.raises(ValueError, match=r"Can't handle .* as a file for mode 'w'"):
        generic_io.get_file(Reader(buff), "w")

    with pytest.raises(ValueError, match=r"Can't handle .* as a file for mode 'r'"):
        generic_io.get_file(Writer(buff), "r")


def test_check_bytes(tmp_path):
    with open(os.path.join(str(tmp_path), "test.asdf"), "w", encoding="utf-8") as fd:
        assert generic_io._check_bytes(fd, "r") is False
        assert generic_io._check_bytes(fd, "rw") is False
        assert generic_io._check_bytes(fd, "w") is False

    with open(os.path.join(str(tmp_path), "test.asdf"), "wb") as fd:
        assert generic_io._check_bytes(fd, "r") is True
        assert generic_io._check_bytes(fd, "rw") is True
        assert generic_io._check_bytes(fd, "w") is True


def test_truncated_reader():
    """
    Tests several edge cases for _TruncatedReader.read()

    Includes regression test for
    https://github.com/asdf-format/asdf/pull/181
    """

    # TODO: Should probably break this up into multiple test cases

    fd = generic_io.RandomAccessFile(io.BytesIO(), "rw")
    content = b"a" * 100 + b"b"
    fd.write(content)
    fd.seek(0)

    # Simple cases where the delimiter is not found at all
    tr = generic_io._TruncatedReader(fd, b"x", 1)
    with pytest.raises(exceptions.DelimiterNotFoundError, match=r"b'x' not found"):
        tr.read()

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"x", 1)
    assert tr.read(100) == content[:100]
    assert tr.read(1) == content[100:]
    with pytest.raises(exceptions.DelimiterNotFoundError, match=r"b'x' not found"):
        tr.read()

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"x", 1, exception=False)
    assert tr.read() == content

    # No delimiter but with 'initial_content'
    init = b"abcd"
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"x", 1, initial_content=init, exception=False)
    assert tr.read(100) == (init + content)[:100]
    assert tr.read() == (init + content)[100:]

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"x", 1, initial_content=init, exception=False)
    assert tr.read() == init + content

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"x", 1, initial_content=init, exception=False)
    assert tr.read(2) == init[:2]
    assert tr.read() == init[2:] + content

    # Some tests of a single character delimiter
    # Add some trailing data after the delimiter
    fd.seek(0, 2)
    fd.write(b"ffff")

    # Delimiter not included in read
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"b", 1)
    assert tr.read(100) == content[:100]
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"b", 1)
    assert tr.read() == content[:100]

    # Delimiter included
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"b", 1, include=True)
    assert tr.read() == content[:101]
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"b", 1, include=True)
    assert tr.read(101) == content[:101]
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"b", 1, include=True)
    assert tr.read(102) == content[:101]
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, b"b", 1, include=True)
    assert tr.read(100) == content[:100]
    assert tr.read(1) == content[100:101]
    assert tr.read() == b""

    # Longer delimiter with variable length
    content = b"a" * 100 + b"\n...\n" + b"ffffff"
    delimiter = rb"\r?\n\.\.\.((\r?\n)|$)"
    readahead = 7

    fd = generic_io.RandomAccessFile(io.BytesIO(), "rw")
    fd.write(content)

    # Delimiter not included in read
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read() == content[:100]
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(100) == content[:100]
    assert tr.read() == b""

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(99) == content[:99]
    assert tr.read() == content[99:100]
    assert tr.read() == b""

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(99) == content[:99]
    assert tr.read(2) == content[99:100]
    assert tr.read() == b""

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead)
    assert tr.read(99) == content[:99]
    assert tr.read(50) == content[99:100]
    assert tr.read() == b""

    # Same as the previous set of tests, but including the delimiter
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read() == content[:105]
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(105) == content[:105]
    assert tr.read() == b""

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(99) == content[:99]
    assert tr.read() == content[99:105]
    assert tr.read() == b""

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(99) == content[:99]
    assert tr.read(2) == content[99:101]
    assert tr.read() == content[101:105]
    assert tr.read() == b""

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True)
    assert tr.read(99) == content[:99]
    assert tr.read(50) == content[99:105]
    assert tr.read() == b""

    # Same sequence of tests but with some 'initial_content'
    init = b"abcd"

    # Delimiter not included in read
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, initial_content=init)
    assert tr.read() == (init + content[:100])
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, initial_content=init)
    assert tr.read(100) == (init + content[:96])
    assert tr.read() == content[96:100]
    assert tr.read() == b""

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read() == content[95:100]
    assert tr.read() == b""

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(6) == content[95:100]
    assert tr.read() == b""

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(50) == content[95:100]
    assert tr.read() == b""

    # Same as the previous set of tests, but including the delimiter
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True, initial_content=init)
    assert tr.read() == (init + content[:105])
    assert tr.read() == b""

    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True, initial_content=init)
    assert tr.read(105) == (init + content[:101])
    assert tr.read() == content[101:105]
    assert tr.read() == b""

    # (read just up to the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True, initial_content=init)
    assert tr.read(103) == (init + content[:99])
    assert tr.read() == content[99:105]
    assert tr.read() == b""

    # (read partway into the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True, initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(6) == content[95:101]
    assert tr.read() == content[101:105]
    assert tr.read() == b""

    # (read well past the delimiter)
    fd.seek(0)
    tr = generic_io._TruncatedReader(fd, delimiter, readahead, include=True, initial_content=init)
    assert tr.read(99) == (init + content[:95])
    assert tr.read(50) == content[95:105]
    assert tr.read() == b""


def test_blocksize(tree, tmp_path):
    path = os.path.join(str(tmp_path), "test.asdf")

    def get_write_fd():
        # cannot use context manager here because it closes the file
        return generic_io.get_file(open(path, "wb"), mode="w", close=True)

    def get_read_fd():
        # Must open with mode=rw in order to get memmapped data
        # cannot use context manager here because it closes the file
        return generic_io.get_file(open(path, "r+b"), mode="rw", close=True)

    with config_context() as config:
        config.io_block_size = 1233  # make sure everything works with a strange blocksize
        with _roundtrip(tree, get_write_fd, get_read_fd) as ff:
            assert ff._fd.block_size == 1233


def test_io_subclasses(tmp_path):
    ref = b"0123456789"

    b = io.BytesIO(b"0123456789")
    b.seek(0)
    f = generic_io.get_file(b)
    r = f.read(len(ref))
    assert r == ref, (r, ref)
    f.close()

    b = io.BytesIO(b"0123456789")
    b.seek(0)
    br = io.BufferedReader(io.BytesIO(ref))
    f = generic_io.get_file(b)
    assert r == ref, (r, ref)
    f.close()

    b = io.BytesIO(b"")
    bw = io.BufferedWriter(b)
    f = generic_io.get_file(bw, mode="w")
    f.write(ref)
    b.seek(0)
    r = b.read(len(ref))
    assert r == ref, (r, ref)
    f.close()

    b = io.BytesIO(b"")
    br = io.BufferedRandom(b)
    f = generic_io.get_file(br, mode="rw")
    f.write(ref)
    f.seek(0)
    r = f.read(len(ref))
    assert r == ref, (r, ref)
    f.close()


def test_fsspec(tmp_path):
    """
    Issue #1146 reported errors when opening a fsspec 'file'
    This is a regression test for the fix in PR #1226
    """
    fsspec = pytest.importorskip("fsspec")

    ref = b"01234567890"
    fn = tmp_path / "test"

    with fsspec.open(fn, mode="bw+") as f:
        f.write(ref)
        f.seek(0)
        gf = generic_io.get_file(f)
        r = gf.read(len(ref))
        assert r == ref, (r, ref)

        gf.seek(0)
        arr = gf.read_into_array(len(ref))
        for ai, i in zip(arr, ref):
            assert ai == i


@pytest.mark.remote_data()
def test_fsspec_http(httpserver):
    """
    Issue #1146 reported errors when opening a fsspec url (using the http
    filesystem)
    This is a regression test for the fix in PR #1228
    """
    fsspec = pytest.importorskip("fsspec")

    ref = b"01234567890"
    path = os.path.join(httpserver.tmpdir, "test")

    with open(path, "wb") as f:
        f.write(ref)

    fn = httpserver.url + "test"
    with fsspec.open(fn) as f:
        gf = generic_io.get_file(f)
        r = gf.read(len(ref))
        assert r == ref, (r, ref)

        gf.seek(0)
        arr = gf.read_into_array(len(ref))
        for ai, i in zip(arr, ref):
            assert ai == i


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Cannot test write file permissions on windows",
)
@pytest.mark.parametrize("umask", range(512))
def test_write_file_permissions(tmp_path, umask):
    previous_umask = os.umask(umask)
    fn = tmp_path / "foo"
    with generic_io.get_file(fn, mode="w"):
        pass
    permissions = os.stat(fn)[stat.ST_MODE] & 0o777
    os.umask(previous_umask)
    target_permissions = generic_io._FILE_PERMISSIONS_NO_EXECUTE & ~umask
    assert permissions == target_permissions
