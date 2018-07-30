# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
This provides abstractions around a number of different file and
stream types available to Python so that they are always used in the
most efficient way.

The classes in this module should not be instantiated directly, but
instead, one should use the factory function `get_file`.
"""

import io
import math
import os
import platform
import re
import sys
import tempfile
from distutils.version import LooseVersion

from os import SEEK_SET, SEEK_CUR, SEEK_END

import http.client
from urllib import parse as urlparse
from urllib.request import url2pathname

import six

import numpy as np

from . import util
from .extern import atomicfile


__all__ = ['get_file', 'get_uri', 'resolve_uri', 'relative_uri']


_local_file_schemes = ['', 'file']
if sys.platform.startswith('win'):  # pragma: no cover
    import string
    _local_file_schemes.extend(string.ascii_letters)


def _check_bytes(fd, mode):
    """
    Checks whether a given file-like object is opened in binary mode.
    """
    # On Python 3, doing fd.read(0) on an HTTPResponse object causes
    # it to not be able to read any further, so we do this different
    # kind of check, which, unfortunately, is not as robust.
    if isinstance(fd, io.IOBase):
        if isinstance(fd, io.TextIOBase):
            return False
        return True

    if 'r' in mode:
        x = fd.read(0)
        if not isinstance(x, bytes):
            return False
    elif 'w' in mode:
        try:
            fd.write(b'')
        except TypeError:
            return False

    return True


if (sys.platform == 'darwin' and
    LooseVersion(platform.mac_ver()[0]) < LooseVersion('10.9')):  # pragma: no cover
    def _array_fromfile(fd, size):
        chunk_size = 1024 ** 3
        if size < chunk_size:
            return np.fromfile(fd, dtype=np.uint8, count=size)
        else:
            array = np.empty(size, dtype=np.uint8)
            for beg in range(0, size, chunk_size):
                end = min(size, beg + chunk_size)
                array[beg:end] = np.fromfile(fd, dtype=np.uint8, count=end - beg)
            return array
else:
    def _array_fromfile(fd, size):
        return np.fromfile(fd, dtype=np.uint8, count=size)


_array_fromfile.__doc__ = """
Load a binary array from a real file object.

Parameters
----------
fd : real file object

size : integer
    Number of bytes to read.
"""


def _array_tofile_chunked(write, array, chunksize):  # pragma: no cover
    array = array.view(np.uint8).flatten()
    for i in range(0, array.nbytes, chunksize):
        write(array[i:i + chunksize].data)


def _array_tofile_simple(fd, write, array):
    return write(array.data)


if sys.platform == 'darwin':  # pragma: no cover
    def _array_tofile(fd, write, array):
        # This value is currently set as a workaround for a known bug in Python
        # on OSX. Individual writes must be less than 2GB, which necessitates
        # the chunk size here if we want it to remain a power of 2.
        # See https://bugs.python.org/issue24658.
        OSX_WRITE_LIMIT = 2 ** 30
        if fd is None or array.nbytes >= OSX_WRITE_LIMIT and array.nbytes % 4096 == 0:
            return _array_tofile_chunked(write, array, OSX_WRITE_LIMIT)
        return _array_tofile_simple(fd, write, array)
elif sys.platform.startswith('win'):  # pragma: no cover
    def _array_tofile(fd, write, array):
        WIN_WRITE_LIMIT = 2 ** 30
        return _array_tofile_chunked(write, array, WIN_WRITE_LIMIT)
else:
    _array_tofile = _array_tofile_simple


_array_tofile.__doc__ = """
Write an array to a file.

Parameters
----------
fd : real file object
   If fd is provided, must be a real system file as supported by
   numpy.tofile.  May be None, in which case all writing will be done
   through the `write` method.

write : callable
   A callable that writes bytes to the file.

array : Numpy array
   Must be an underlying data array, not a view.
"""


def resolve_uri(base, uri):
    """
    Resolve a URI against a base URI.
    """
    if base is None:
        base = ''
    resolved = urlparse.urljoin(base, uri)
    parsed = urlparse.urlparse(resolved)
    if parsed.path != '' and not parsed.path.startswith('/'):
        raise ValueError(
            "Resolved to relative URL")
    return resolved


def relative_uri(source, target):
    """
    Make a relative URI from source to target.
    """
    su = urlparse.urlparse(source)
    tu = urlparse.urlparse(target)
    extra = list(tu[3:])
    relative = None
    if tu[0] == '' and tu[1] == '':
        if tu[2] == su[2]:
            relative = ''
        elif not tu[2].startswith('/'):
            relative = tu[2]
    elif su[0:2] != tu[0:2]:
        return target

    if relative is None:
        if tu[2] == su[2]:
            relative = ''
        else:
            relative = os.path.relpath(tu[2], os.path.dirname(su[2]))
    if relative == '.':
        relative = ''
    relative = urlparse.urlunparse(["", "", relative] + extra)
    return relative


class _TruncatedReader(object):
    """
    Reads until a given delimiter is found.  Only works with
    RandomAccessFile and InputStream, though as this is a private
    class, this is not explicitly enforced.
    """
    def __init__(self, fd, delimiter, readahead_bytes, delimiter_name=None,
                 include=False, initial_content=b'', exception=True):
        self._fd = fd
        self._delimiter = delimiter
        self._readahead_bytes = readahead_bytes
        if delimiter_name is None:
            delimiter_name = delimiter
        self._delimiter_name = delimiter_name
        self._include = include
        self._initial_content = initial_content
        self._trailing_content = b''
        self._exception = exception
        self._past_end = False

    def read(self, nbytes=None):
        if self._past_end:
            content = self._trailing_content[:nbytes]
            if nbytes is None:
                self._trailing_content = b''
            else:
                self._trailing_content = self._trailing_content[nbytes:]

            return content

        if nbytes is None:
            content = self._fd._peek()
        elif nbytes <= len(self._initial_content):
            content = self._initial_content[:nbytes]
            self._initial_content = self._initial_content[nbytes:]
            return content
        else:
            content = self._fd._peek(nbytes - len(self._initial_content) +
                                     self._readahead_bytes)

        if content == b'':
            if self._exception:
                raise ValueError("{0} not found".format(self._delimiter_name))
            self._past_end = True
            return content

        index = re.search(self._delimiter, content)
        if index is not None:
            if self._include:
                index = index.end()
            else:
                index = index.start()
            content = content[:index]
            self._past_end = True
        elif nbytes is None and self._exception:
            # Read the whole file and didn't find the delimiter
            raise ValueError("{0} not found".format(self._delimiter_name))
        else:
            if nbytes:
                content = content[:nbytes - len(self._initial_content)]

        self._fd.fast_forward(len(content))

        if self._initial_content:
            content = self._initial_content + content
            self._initial_content = b''

        if self._past_end and nbytes:
            self._trailing_content = content[nbytes:]
            content = content[:nbytes]

        return content


@six.add_metaclass(util.InheritDocstrings)
class GenericFile(object):
    """
    Base class for an abstraction layer around a number of different
    file-like types.  Each of its subclasses handles a particular kind
    of file in the most efficient way possible.

    This class should not be instantiated directly, but instead the
    factory function `get_file` should be used to get the correct
    subclass for the given file-like object.
    """
    def __init__(self, fd, mode, close=False, uri=None):
        """
        Parameters
        ----------
        fd : file-like object
            The particular kind of file-like object must match the
            subclass of `GenericFile` being instantiated.

        mode : str
            Must be ``"r"`` (read), ``"w"`` (write), or ``"rw"``
            (read/write).

        close : bool, optional
            When ``True``, close the given `fd` in the ``__exit__``
            method, i.e. at the end of the with block.  Should be set
            to ``True`` when this object "owns" the file object.
            Default: ``False``.

        uri : str, optional
            The file path or URI used to open the file.  This is used
            to resolve relative URIs when the file refers to external
            sources.
        """
        if not _check_bytes(fd, mode):
            raise ValueError(
                "File-like object must be opened in binary mode.")

        self._fd = fd
        self._mode = mode
        self._close = close
        self._blksize = io.DEFAULT_BUFFER_SIZE
        self._size = None
        self._uri = uri

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._close:
            if hasattr(self._fd, '__exit__'):
                self._fd.__exit__(type, value, traceback)
            else:
                self._fd.close()

    @property
    def block_size(self):
        return self._blksize

    @property
    def mode(self):
        """
        The mode of the file.  Will be ``'r'``, ``'w'`` or ``'rw'``.
        """
        return self._mode

    @property
    def uri(self):
        """
        The base uri of the file.
        """
        return self._uri

    def read(self, size=-1):
        """
        Read at most size bytes from the file (less if the read hits
        EOF before obtaining size bytes). If the size argument is
        negative or omitted, read all data until EOF is reached. The
        bytes are returned as a `bytes` object. An empty `bytes`
        object is returned when EOF is encountered immediately.

        Only available if `readable` returns `True`.
        """
        # On Python 3, reading 0 bytes from a socket causes it to stop
        # working, so avoid doing that at all costs.
        if size == 0:
            return b''
        return self._fd.read(size)

    def read_block(self):
        """
        Read a "block" from the file.  For real filesystem files, the
        block is the size of a native filesystem block.
        """
        return self.read(self._blksize)

    def read_blocks(self, size):
        """
        Read ``size`` bytes of data from the file, one block at a
        time.  The result is a generator where each value is a bytes
        object.
        """
        i = 0
        for i in range(0, size - self._blksize, self._blksize):
            yield self.read(self._blksize)
        if i < size:
            yield self.read(size - i)

    def write(self, content):
        self._fd.write(content)

    write.__doc__ = """
    Write a string to the file. There is no return value. Due to
    buffering, the string may not actually show up in the file
    until the flush() or close() method is called.

    Only available if `writable` returns `True`.
    """

    def write_array(self, array):
        _array_tofile(None, self.write, np.ascontiguousarray(array))

    def seek(self, offset, whence=0):
        """
        Set the file's current position.  Only available if `seekable`
        returns `True`.

        Parameters
        ----------
        offset : integer
            Offset, in bytes.

        whence : integer, optional
            The `whence` argument is optional and defaults to
            SEEK_SET or 0 (absolute file positioning); other values
            are SEEK_CUR or 1 (seek relative to the current
            position) and SEEK_END or 2 (seek relative to the
            file’s end).
        """
        result = self._fd.seek(offset, whence)
        self.tell()
        return result

    def tell(self):
        """
        Return the file's current position, in bytes.  Only available
        in `seekable` returns `True`.
        """
        return self._fd.tell()

    def flush(self):
        """
        Flush the internal buffer.
        """
        self._fd.flush()

    def close(self):
        """
        Close the file.  The underlying file-object will only be
        closed if ``close=True`` was passed to the constructor.
        """
        if self._close:
            self._fd.close()

    def truncate(self, size=None):
        """
        Truncate the file to the given size.
        """
        raise NotImplementedError()

    def writable(self):
        """
        Returns `True` if the file can be written to.
        """
        return 'w' in self.mode

    def readable(self):
        """
        Returns `True` if the file can be read from.
        """
        return 'r' in self.mode

    def seekable(self):
        """
        Returns `True` if the file supports random access (`seek` and
        `tell`).
        """
        return False

    def can_memmap(self):
        """
        Returns `True` if the file supports memmapping.
        """
        return False

    def is_closed(self):
        """
        Returns `True` if the underlying file object is closed.
        """
        return self._fd.closed

    def read_until(self, delimiter, readahead_bytes, delimiter_name=None,
                   include=True, initial_content=b'', exception=True):
        """
        Reads until a match for a given regular expression is found.

        Parameters
        ----------
        delimiter : str
            A regular expression.

        readahead_bytes : int
            The number of bytes to read ahead to make sure the
            delimiter isn't on a block boundary.

        delimiter_name : str, optional
            The name of the delimiter.  Used in error messages if the
            delimiter is not found.  If not provided, the raw content
            of `delimiter` will be used.

        include : bool, optional
            When ``True``, include the delimiter in the result.

        initial_content : bytes, optional
            Additional content to include at the beginning of the
            first read.

        exception : bool, optional
            If ``True`` (default), raise an exception if the end
            marker isn't found.

        Returns
        -------
        content : bytes
            The content from the current position in the file, up to
            the delimiter.  Includes the delimiter if `include` is
            ``True``.

        Raises
        ------
        ValueError :
            If the delimiter is not found before the end of the file.
        """
        buff = io.BytesIO()
        reader = self.reader_until(
            delimiter, readahead_bytes, delimiter_name=delimiter_name,
            include=include, initial_content=initial_content,
            exception=exception)
        while True:
            content = reader.read(self.block_size)
            buff.write(content)
            if len(content) < self.block_size:
                break
        return buff.getvalue()

    def reader_until(self, delimiter, readahead_bytes,
                     delimiter_name=None, include=True,
                     initial_content=b'', exception=True):
        """
        Returns a readable file-like object that treats the given
        delimiter as the end-of-file.

        Parameters
        ----------
        delimiter : str
            A regular expression.

        readahead_bytes : int
            The number of bytes to read ahead to make sure the
            delimiter isn't on a block boundary.

        delimiter_name : str, optional
            The name of the delimiter.  Used in error messages if the
            delimiter is not found.  If not provided, the raw content
            of `delimiter` will be used.

        include : bool, optional
            When ``True``, include the delimiter in the result.

        initial_content : bytes, optional
            Additional content to include at the beginning of the
            first read.

        exception : bool, optional
            If ``True`` (default), raise an exception if the end
            marker isn't found.

        Raises
        ------
        ValueError :
            If the delimiter is not found before the end of the file.
        """
        raise NotImplementedError()

    def seek_until(self, delimiter, readahead_bytes, delimiter_name=None,
                   include=True, initial_content=b'', exception=True):
        """
        Seeks in the file until a match for a given regular expression
        is found.  This is similar to ``read_until``, except the
        intervening content is not retained.

        Parameters
        ----------
        delimiter : str
            A regular expression.

        readahead_bytes : int
            The number of bytes to read ahead to make sure the
            delimiter isn't on a block boundary.

        delimiter_name : str, optional
            The name of the delimiter.  Used in error messages if the
            delimiter is not found.  If not provided, the raw content
            of `delimiter` will be used.

        include : bool, optional
            When ``True``, include the delimiter in the result.

        initial_content : bytes, optional
            Additional content to include at the beginning of the
            first read.

        exception : bool, optional
            If ``True`` (default), raise an exception if the end
            marker isn't found.

        Returns
        -------
        content : bytes
            The content from the current position in the file, up to
            the delimiter.  Includes the delimiter if `include` is
            ``True``.

        Raises
        ------
        ValueError :
            If the delimiter is not found before the end of the file.
        """
        reader = self.reader_until(
            delimiter, readahead_bytes, delimiter_name=delimiter_name,
            include=include, initial_content=initial_content,
            exception=exception)
        while True:
            try:
                content = reader.read(self.block_size)
            except ValueError:
                return False
            if content == b'':
                return True

    def fast_forward(self, size):
        """
        Move the file position forward by `size`.
        """
        raise NotImplementedError()

    def clear(self, nbytes):
        """
        Write nbytes of zeros.
        """
        blank_data = b'\0' * self.block_size
        for i in range(0, nbytes, self.block_size):
            length = min(nbytes - i, self.block_size)
            self.write(blank_data[:length])

    def memmap_array(self, offset, size):
        """
        Memmap a chunk of the file into a `np.core.memmap` object.

        Parameters
        ----------
        offset : integer
            The offset, in bytes, in the file.

        size : integer
            The size of the data to memmap.

        Returns
        -------
        array : np.core.memmap
        """
        raise NotImplementedError()

    def read_into_array(self, size):
        """
        Read a chunk of the file into a uint8 array.

        Parameters
        ----------
        size : integer
            The size of the data.

        Returns
        -------
        array : np.core.memmap
        """
        buff = self.read(size)
        return np.frombuffer(buff, np.uint8, size, 0)


class GenericWrapper(object):
    """
    A wrapper around a `GenericFile` object so that closing only
    happens in the very outer layer.
    """
    def __init__(self, fd):
        self._fd = fd

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def __getattr__(self, attr):
        return getattr(self._fd, attr)


class RandomAccessFile(GenericFile):
    """
    The base class of file types that support random access.
    """
    def seekable(self):
        return True

    def _peek(self, size=-1):
        cursor = self.tell()
        content = self.read(size)
        self.seek(cursor, SEEK_SET)
        return content

    def reader_until(self, delimiter, readahead_bytes, delimiter_name=None,
                     include=True, initial_content=b'', exception=True):
        return _TruncatedReader(
            self, delimiter, readahead_bytes, delimiter_name=delimiter_name,
            include=include, initial_content=initial_content,
            exception=exception)

    def fast_forward(self, size):
        if size < 0:
            self.seek(0, SEEK_END)
        self.seek(size, SEEK_CUR)

    if sys.platform.startswith('win'):  # pragma: no cover
        def truncate(self, size=None):
            # ftruncate doesn't work on an open file in Windows.  The
            # best we can do is clear the extra bytes or add extra
            # bytes to the end.
            if size is None:
                size = self.tell()

            self.seek(0, SEEK_END)
            file_size = self.tell()
            if size < file_size:
                self.seek(size, SEEK_SET)
                nbytes = file_size - size
            elif size > file_size:
                nbytes = size - file_size
            else:
                nbytes = 0

            block = b'\0' * self.block_size
            while nbytes > 0:
                self.write(block[:min(nbytes, self.block_size)])
                nbytes -= self.block_size

            self.seek(size, SEEK_SET)
    else:
        def truncate(self, size=None):
            if size is None:
                self._fd.truncate()
            else:
                self._fd.truncate(size)
                self.seek(size, SEEK_SET)


class RealFile(RandomAccessFile):
    """
    Handles "real" files on a filesystem.
    """
    def __init__(self, fd, mode, close=False, uri=None):
        super(RealFile, self).__init__(fd, mode, close=close, uri=uri)
        stat = os.fstat(fd.fileno())
        if sys.platform.startswith('win'):  # pragma: no cover
            # There appears to be reliable way to get block size on Windows,
            # so just choose a reasonable default
            self._blksize = io.DEFAULT_BUFFER_SIZE
        else:
            self._blksize = stat.st_blksize
        self._size = stat.st_size
        if (uri is None and
            isinstance(fd.name, str)):
            self._uri = util.filepath_to_url(os.path.abspath(fd.name))

    def write_array(self, arr):
        if isinstance(arr, np.memmap) and getattr(arr, 'fd', None) is self:
            arr.flush()
            self.fast_forward(len(arr.data))
        else:
            _array_tofile(self._fd, self._fd.write, np.ascontiguousarray(arr))

    def can_memmap(self):
        return True

    def memmap_array(self, offset, size):
        if 'w' in self._mode:
            mode = 'r+'
        else:
            mode = 'r'
        mmap = np.memmap(
            self._fd, mode=mode, offset=offset, shape=size)
        mmap.fd = self
        return mmap

    def read_into_array(self, size):
        return _array_fromfile(self._fd, size)


class MemoryIO(RandomAccessFile):
    """
    Handles random-access memory buffers, mainly `io.BytesIO` and
    `StringIO.StringIO`.
    """
    def __init__(self, fd, mode, uri=None):
        super(MemoryIO, self).__init__(fd, mode, uri=uri)
        tell = fd.tell()
        fd.seek(0, 2)
        self._size = fd.tell()
        fd.seek(tell, 0)

    def read_into_array(self, size):
        buf = self._fd.getvalue()
        offset = self._fd.tell()
        result = np.frombuffer(buf, np.uint8, size, offset)
        # Copy the buffer so the original memory can be released.
        result = result.copy()
        self.seek(size, SEEK_CUR)
        return result


class InputStream(GenericFile):
    """
    Handles an input stream, such as stdin.
    """
    def __init__(self, fd, mode='r', close=False, uri=None):
        super(InputStream, self).__init__(fd, mode, close=close, uri=uri)
        self._fd = fd
        self._buffer = b''

    def _peek(self, size=-1):
        if size < 0:
            self._buffer += self._fd.read()
        else:
            len_buffer = len(self._buffer)
            if len_buffer < size:
                self._buffer += self._fd.read(size - len_buffer)
        return self._buffer

    def read(self, size=-1):
        # On Python 3, reading 0 bytes from a socket causes it to stop
        # working, so avoid doing that at all costs.
        if size == 0:
            return b''

        len_buffer = len(self._buffer)
        if len_buffer == 0:
            return self._fd.read(size)
        elif size < 0:
            self._buffer += self._fd.read()
            buffer = self._buffer
            self._buffer = b''
            return buffer
        elif len_buffer < size:
            if len_buffer < size:
                self._buffer += self._fd.read(size - len(self._buffer))
            buffer = self._buffer
            self._buffer = b''
            return buffer
        else:
            buffer = self._buffer[:size]
            self._buffer = self._buffer[size:]
            return buffer

    def reader_until(self, delimiter, readahead_bytes, delimiter_name=None,
                     include=True, initial_content=b'', exception=True):
        return _TruncatedReader(
            self, delimiter, readahead_bytes, delimiter_name=delimiter_name,
            include=include, initial_content=initial_content,
            exception=exception)

    def fast_forward(self, size):
        if size >= 0 and len(self.read(size)) != size:
            raise IOError("Read past end of file")

    def read_into_array(self, size):
        try:
            # See if Numpy can handle this as a real file first...
            return np.fromfile(self._fd, np.uint8, size)
        except (IOError, AttributeError):
            # Else, fall back to reading into memory and then
            # returning the Numpy array.
            data = self.read(size)
            # We need to copy the array, so it is writable
            result = np.frombuffer(data, np.uint8, size)
            # When creating an array from a buffer, it is read-only.
            # If we need a read/write array, we have to copy it.
            if 'w' in self._mode:
                result = result.copy()
            return result


class OutputStream(GenericFile):
    """
    Handles an output stream, such as stdout.
    """
    def __init__(self, fd, close=False, uri=None):
        super(OutputStream, self).__init__(fd, 'w', close=close, uri=uri)
        self._fd = fd

    def fast_forward(self, size):
        if size < 0:
            return
        self.clear(size)


class HTTPConnection(RandomAccessFile):
    """
    Uses a persistent HTTP connection to request specific ranges of
    the file and obtain its structure without transferring it in its
    entirety.

    It creates a temporary file on the local filesystem and copies
    blocks into it as needed.  The `_blocks` array is a bitfield that
    keeps track of which blocks we have.
    """
    # TODO: Handle HTTPS connection

    def __init__(self, connection, size, path, uri, first_chunk):
        self._mode = 'r'
        self._blksize = io.DEFAULT_BUFFER_SIZE
        # The underlying HTTPConnection object doesn't track closed
        # status, so we do that here.
        self._closed = False
        self._fd = connection
        self._path = path
        self._uri = uri

        # A bitmap of the blocks that we've already read and cached
        # locally
        self._blocks = np.zeros(
            int(math.ceil(size / self._blksize / 8)), np.uint8)

        local_file = tempfile.TemporaryFile()
        self._local = RealFile(local_file, 'rw', close=True)
        self._local.truncate(size)
        self._local.seek(0)
        self._local.write(first_chunk)
        self._local.seek(0)
        self._blocks[0] = 1

        # The size of the entire file
        self._size = size
        self._nreads = 0

        # Some methods just short-circuit to the local copy
        self.seek = self._local.seek
        self.tell = self._local.tell

    def __exit__(self, type, value, traceback):
        if not self._closed:
            self._local.close()
            if hasattr(self._fd, '__exit__'):
                self._fd.__exit__(type, value, traceback)
            else:
                self._fd.close()
            self._closed = True

    def close(self):
        if not self._closed:
            self._local.close()
            self._fd.close()
            self._closed = True

    def is_closed(self):
        return self._closed

    def _get_range(self, start, end):
        """
        Ensure the range of bytes has been copied to the local cache.
        """
        if start >= self._size:
            return

        end = min(end, self._size)

        blocks = self._blocks
        block_size = self.block_size

        def has_block(x):
            return blocks[x >> 3] & (1 << (x & 0x7))

        def mark_block(x):
            blocks[x >> 3] |= (1 << (x & 0x7))

        block_start = start // block_size
        block_end = end // block_size + 1

        pos = self._local.tell()

        try:
            # Between block_start and block_end, some blocks may be
            # already loaded.  We want to load all of the missing
            # blocks in as few requests as possible.
            a = block_start
            while a < block_end:
                # Skip over whole groups of blocks at a time
                while a < block_end and blocks[a >> 3] == 0xff:
                    a = ((a >> 3) + 1) << 3
                while a < block_end and has_block(a):
                    a += 1
                if a >= block_end:
                    break

                b = a + 1
                # Skip over whole groups of blocks at a time
                while b < block_end and blocks[b >> 3] == 0x0:
                    b = ((b >> 3) + 1) << 3
                while b < block_end and not has_block(b):
                    b += 1
                if b > block_end:
                    b = block_end

                if a * block_size >= self._size:
                    return

                headers = {
                    'Range': 'bytes={0}-{1}'.format(
                        a * block_size, (b * block_size) - 1)}
                self._fd.request('GET', self._path, headers=headers)
                response = self._fd.getresponse()
                if response.status != 206:
                    raise IOError("HTTP failed: {0} {1}".format(
                        response.status, response.reason))

                # Now copy over to the temporary file, block-by-block
                self._local.seek(a * block_size, os.SEEK_SET)
                for i in range(a, b):
                    chunk = response.read(block_size)
                    self._local.write(chunk)
                    mark_block(i)
                response.close()

                self._nreads += 1

                a = b
        finally:
            self._local.seek(pos, os.SEEK_SET)

    def read(self, size=-1):
        if self._closed:
            raise IOError("read from closed connection")

        pos = self._local.tell()

        # Adjust size so it doesn't go beyond the end of the file
        if size < 0 or pos + size > self._size:
            size = self._size - pos

        # On Python 3, reading 0 bytes from a socket causes it to stop
        # working, so avoid doing that at all costs.
        if size == 0:
            return b''

        self._get_range(pos, pos + size)
        return self._local.read(size)

    def read_into_array(self, size):
        if self._closed:
            raise IOError("read from closed connection")

        pos = self._local.tell()

        if pos + size > self._size:
            raise IOError("Read past end of file.")

        self._get_range(pos, pos + size)
        return self._local.memmap_array(pos, size)


def _make_http_connection(init, mode, uri=None):
    """
    Creates a HTTPConnection instance if the HTTP server supports
    Range requests, otherwise falls back to a generic InputStream.
    """
    parsed = urlparse.urlparse(init)
    connection = http.client.HTTPConnection(parsed.netloc)
    connection.connect()

    block_size = io.DEFAULT_BUFFER_SIZE

    # We request a range of the whole file ("0-") to check if the
    # server understands that header entry, and also to get the
    # size of the entire file
    headers = {'Range': 'bytes=0-'}
    connection.request('GET', parsed.path, headers=headers)
    response = connection.getresponse()
    if response.status // 100 != 2:
        raise IOError("HTTP failed: {0} {1}".format(
            response.status, response.reason))

    # Status 206 means a range was returned.  If it's anything else
    # that indicates the server probably doesn't support Range
    # headers.
    if (response.status != 206 or
        response.getheader('accept-ranges', None) != 'bytes' or
        response.getheader('content-range', None) is None or
        response.getheader('content-length', None) is None):
        # Fall back to a regular input stream, but we don't
        # need to open a new connection.
        response.close = connection.close
        return InputStream(response, mode, uri=uri or init, close=True)

    # Since we'll be requesting chunks, we can't read at all with the
    # current request (because we can't abort it), so just close and
    # start over
    size = int(response.getheader('content-length'))
    first_chunk = response.read(block_size)
    response.close()
    return HTTPConnection(connection, size, parsed.path, uri or init,
                          first_chunk)

def get_uri(file_obj):
    """
    Returns the uri of the given file object

    Parameters
    ----------
    uri : object
    """
    if isinstance(file_obj, six.string_types):
        return file_obj
    if isinstance(file_obj, GenericFile):
        return file_obj.uri

    # A catch-all for types from Python's io module that have names
    return getattr(file_obj, 'name', '')


def get_file(init, mode='r', uri=None):
    """
    Returns a `GenericFile` instance suitable for wrapping the given
    object `init`.

    If passed an already open file-like object, it must be opened for
    reading/writing in binary mode.  It is the caller's responsibility
    to close it.

    Parameters
    ----------
    init : object
        `init` may be:

        - A `bytes` or `unicode` file path or ``file:`` or ``http:``
          url.

        - A Python 2 `file` object.

        - An `io.IOBase` object (the default file object on Python 3).

        - A ducktyped object that looks like a file object.  If `mode`
          is ``"r"``, it must have a ``read`` method.  If `mode` is
          ``"w"``, it must have a ``write`` method.  If `mode` is
          ``"rw"`` it must have the ``read``, ``write``, ``tell`` and
          ``seek`` methods.

        - A `GenericFile` instance, in which case it is wrapped in a
          `GenericWrapper` instance, so that the file is closed when
          only when the final layer is unwrapped.

    mode : str
        Must be one of ``"r"``, ``"w"`` or ``"rw"``.

    uri : str
        Sets the base URI of the file object.  This will be used to
        resolve any relative URIs contained in the file.  This is
        redundant if `init` is a `bytes` or `unicode` object (since it
        will be the uri), and it may be determined automatically if
        `init` refers to a regular filesystem file.  It is not required
        if URI resolution is not used in the file.

    Returns
    -------
    fd : GenericFile

    Raises
    ------
    ValueError, TypeError, IOError
    """
    if mode not in ('r', 'w', 'rw'):
        raise ValueError("mode must be 'r', 'w' or 'rw'")

    if init in (sys.__stdout__, sys.__stdin__, sys.__stderr__):
        init = os.fdopen(init.fileno(), init.mode + 'b')

    if isinstance(init, (GenericFile, GenericWrapper)):
        if mode not in init.mode:
            raise ValueError(
                "File is opened as '{0}', but '{1}' was requested".format(
                    init.mode, mode))
        return GenericWrapper(init)

    elif isinstance(init, str):
        parsed = urlparse.urlparse(init)
        if parsed.scheme == 'http':
            if 'w' in mode:
                raise ValueError(
                    "HTTP connections can not be opened for writing")
            return _make_http_connection(init, mode, uri=uri)
        elif parsed.scheme in _local_file_schemes:
            if mode == 'rw':
                realmode = 'r+b'
            else:
                realmode = mode + 'b'
            realpath = url2pathname(parsed.path)
            if mode == 'w':
                fd = atomicfile.atomic_open(realpath, realmode)
            else:
                fd = open(realpath, realmode)
            fd = fd.__enter__()
            return RealFile(fd, mode, close=True, uri=uri)

    elif isinstance(init, io.BytesIO):
        return MemoryIO(init, mode, uri=uri)

    elif isinstance(init, io.StringIO):
        raise TypeError(
            "io.StringIO objects are not supported.  Use io.BytesIO instead.")

    elif isinstance(init, io.IOBase):
        if (('r' in mode and not init.readable()) or
            ('w' in mode and not init.writable())):
            raise ValueError(
                "File is opened as '{0}', but '{1}' was requested".format(
                    init.mode, mode))

        if init.seekable():
            if isinstance(init, (io.BufferedReader,
                                 io.BufferedWriter,
                                 io.BufferedRandom)):
                init2 = init.raw
            else:
                init2 = init
            if isinstance(init2, io.RawIOBase):
                result = RealFile(init2, mode, uri=uri)
            else:
                result = MemoryIO(init2, mode, uri=uri)
            result._secondary_fd = init
            return result
        else:
            if mode == 'w':
                return OutputStream(init, uri=uri)
            elif mode == 'r':
                return InputStream(init, mode, uri=uri)
            else:
                raise ValueError(
                    "File '{0}' could not be opened in 'rw' mode".format(init))

    elif mode == 'w' and (
          hasattr(init, 'write') and
          hasattr(init, 'seek') and
          hasattr(init, 'tell')):
        return MemoryIO(init, mode, uri=uri)

    elif mode == 'r' and (
          hasattr(init, 'read') and
          hasattr(init, 'seek') and
          hasattr(init, 'tell')):
        return MemoryIO(init, mode, uri=uri)

    elif mode == 'rw' and (
          hasattr(init, 'read') and
          hasattr(init, 'write') and
          hasattr(init, 'seek') and
          hasattr(init, 'tell')):
        return MemoryIO(init, mode, uri=uri)

    elif mode == 'w' and hasattr(init, 'write'):
        return OutputStream(init, uri=uri)

    elif mode == 'r' and hasattr(init, 'read'):
        return InputStream(init, mode, uri=uri)

    raise ValueError("Can't handle '{0}' as a file for mode '{1}'".format(
        init, mode))
