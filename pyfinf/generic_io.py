# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
This provides abstractions around a number of different file and
stream types available to Python so that they are always used in the
most efficient way.

The classes in this module should not be instantiated directly, but
instead, one should use the factory function `get_file`.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import math
import os
import re
import sys

from astropy.extern import six
from astropy.extern.six.moves.urllib import parse as urlparse
from astropy.utils.misc import InheritDocstrings

import numpy as np


__all__ = ['get_file']


def _check_bytes(fd, mode):
    """
    Checks whether a given file-like object is opened in binary mode.
    """
    if mode == 'r':
        x = fd.read(0)
        if not isinstance(x, bytes):
            return False
    elif mode == 'w':
        if six.PY2 and isinstance(fd, file):
            if 'b' not in fd.mode:
                return False
        else:
            try:
                fd.write(b'')
            except TypeError:
                return False

    return True


@six.add_metaclass(InheritDocstrings)
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
        if mode not in ('r', 'w', 'rw'):
            raise ValueError("mode must be 'r', 'w' or 'rw'")

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
        self.close()

    @property
    def mode(self):
        """
        The mode of the file.  Will be ``'r'``, ``'w'`` or ``'rw'``.
        """
        return self._mode

    def read(self, size=-1):
        """
        Read at most size bytes from the file (less if the read hits
        EOF before obtaining size bytes). If the size argument is
        negative or omitted, read all data until EOF is reached. The
        bytes are returned as a `bytes` object. An empty `bytes`
        object is returned when EOF is encountered immediately.

        Only available if `readable` returns `True`.
        """
        return self._fd.read(size)

    def read_block(self):
        """
        Read a "block" from the file.  For real filesystem files, the
        block is the size of a native filesystem block.
        """
        return self.read(self._blksize)

    def write(self, content):
        """
        Write a string to the file. There is no return value. Due to
        buffering, the string may not actually show up in the file
        until the flush() or close() method is called.

        Only available if `writable` returns `True`.
        """
        self._fd.write(content)

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
            os.SEEK_SET or 0 (absolute file positioning); other values
            are os.SEEK_CUR or 1 (seek relative to the current
            position) and os.SEEK_END or 2 (seek relative to the
            file’s end).
        """
        self._fd.seek(offset, whence)

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

    def read_until(self, delimiter, delimiter_name=None, include=True):
        """
        Reads until a match for a given regular expression is found.

        Parameters
        ----------
        delimiter : str
            A regular expression.

        delimiter_name : str, optional
            The name of the delimiter.  Used in error messages if the
            delimiter is not found.  If not provided, the raw content
            of `delimiter` will be used.

        include : bool, optional
            When ``True``, include the delimiter in the result.

        Returns
        -------
        content : bytes
            The content from the current position in the file, up to
            the delimiter.  Includes the delimiter if `include` is
            ``True``.

        Raises
        ------
        IOError :
            If the delimiter is not found before the end of the file.
        """
        raise NotImplementedError()

    def seek_until(self, delimiter, include=True):
        """
        Seeks in the file until a match for a given regular expression
        is found.  This is similar to ``read_until``, except the
        intervening content is not retained.

        Parameters
        ----------
        delimiter : str
            A regular expression.

        include : bool, optional
            When ``True``, advance past the delimiter.  When
            ``False``, the resulting file position will be at the
            beginning of the delimiter.

        Returns
        -------
        found : bool
            Returns ``True`` if the delimiter was found, else
            ``False``.
        """
        raise NotImplementedError()

    def fast_forward(self, size):
        """
        Move the file position forward by `size`.
        """
        raise NotImplementedError()

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


class GenericWrapper(object):
    """
    A wrapper around a `GenericFile` object so that closing only
    happens in the very outer layer.
    """
    def __init__(self, fd, uri=None):
        self._fd = fd
        if uri is not None:
            self._uri = uri

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

    def read_until(self, delimiter, delimiter_name=None, include=True):
        cursor = self.tell()
        buff = io.BytesIO()
        while True:
            block = self.read_block()
            if len(block) == 0:
                break
            index = re.search(delimiter, block)
            if index is not None:
                if include:
                    index = index.end()
                else:
                    index = index.start()
                block = block[:index]
                buff.write(block)
                self.seek(cursor + buff.tell(), os.SEEK_SET)
                return buff.getvalue()
            buff.write(block)

        if delimiter_name is None:
            delimiter_name = delimiter
        raise IOError("{0} not found".format(delimiter_name))

    def seek_until(self, delimiter, include=True):
        while True:
            block = self.read_block()
            if not len(block):
                return False
            index = re.search(delimiter, block)
            if index is not None:
                if include:
                    index = index.end()
                else:
                    index = index.start()
                self.seek(-(len(block) - index), os.SEEK_CUR)
                return True

        return False

    def fast_forward(self, size):
        self.seek(size, os.SEEK_CUR)


class RealFile(RandomAccessFile):
    """
    Handles "real" files on a filesystem.
    """
    def __init__(self, fd, mode, close=True, uri=None):
        super(RealFile, self).__init__(fd, mode, close=close, uri=uri)
        stat = os.fstat(fd.fileno())
        self._blksize = stat.st_blksize
        self._size = stat.st_size
        if uri is None and os.path.exists(fd.name):
            self._uri = os.path.abspath(fd.name)

    def can_memmap(self):
        return True

    def memmap_array(self, offset, size):
        return np.memmap(
            self._fd, mode=self._mode, offset=offset, shape=size)

    def read_into_array(self, size):
        return np.fromfile(self._fd, np.uint8, size)


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
        return np.frombuffer(
            self._fd.getvalue(), np.uint8, size, self._fd.tell())


class InputStream(GenericFile):
    """
    Handles an input stream, such as stdin.
    """
    def __init__(self, fd, close=False, uri=None):
        super(InputStream, self).__init__(fd, 'r', close=close, uri=uri)
        self._fd = fd
        self._buffer = b''

    def _peek(self, size):
        len_buffer = len(self._buffer)
        if len_buffer < size:
            self._buffer += self._fd.read(size - len_buffer)
        return self._buffer

    def read(self, size=-1):
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

    def read_until(self, delimiter, delimiter_name, include=True):
        buff = io.BytesIO()
        while True:
            block = self._peek(self._blksize)
            if len(block) == 0:
                break
            index = re.search(delimiter, block)
            if index is not None:
                if include:
                    index = index.end()
                else:
                    index = index.start()
                if index != 0:
                    self.read(index)
                block = block[:index]
                buff.write(block)
                return buff.getvalue()
            else:
                self.read(len(block))
            buff.write(block)

        raise IOError("{0} not found".format(delimiter_name))

    def seek_until(self, delimiter, include=True):
        while True:
            block = self._peek(self._blksize)
            if not len(block):
                return False
            index = re.search(delimiter, block)
            if index is not None:
                if include:
                    index = index.end()
                else:
                    index = index.start()
                if index != 0:
                    self.read(index)
                return True
            else:
                self.read(len(block))

        return False

    def fast_forward(self, size):
        if len(self.read(size)) != size:
            raise IOError("Read past end of file")

    def read_into_array(self, size):
        data = self.read(size)
        return np.frombuffer(data, np.uint8, size)


class OutputStream(GenericFile):
    """
    Handles an output stream, such as stdout.
    """
    def __init__(self, fd, close=False, uri=None):
        super(OutputStream, self).__init__(fd, 'w', close=close, uri=uri)
        self._fd = fd

    def fast_forward(self, size):
        written = 0
        block = b' ' * self._blksize
        while written + self._blksize < size:
            self._fd.write(block)
            written += self._blksize
        self._fd.write(block[:size - written])


class HTTPConnection(RandomAccessFile):
    """
    Uses a persistent HTTP connection to request specific ranges of
    the file and obtain its structure without transferring it in its
    entirety.
    """
    # TODO: Handle HTTPS connection

    def __init__(self, connection, size, path, uri):
        self._mode = 'r'
        self._blksize = io.DEFAULT_BUFFER_SIZE
        # The underlying HTTPConnection object doesn't track closed
        # status, so we do that here.
        self._closed = False
        self._fd = connection
        self._path = path
        self._uri = uri
        # The logical position in the file
        self._pos = 0
        # The start and end bytes of the buffer
        self._buffer_start = 0
        self._buffer_end = 0
        self._buffer = b''
        # The size of the entire file
        self._size = size
        self._nreads = 0

    def close(self):
        if not self._closed:
            self._fd.close()
            self._closed = True

    def is_closed(self):
        return self._closed

    def _get_range(self, start, end):
        """
        Get a range of bytes from the server.
        """
        headers = {
            'Range': 'bytes={0}-{1}'.format(start, end - 1)}
        self._fd.request('GET', self._path, headers=headers)
        response = self._fd.getresponse()
        if response.status != 206:
            raise IOError("HTTP failed: {0} {1}".format(
                response.status, response.reason))
        self._nreads += 1
        return response

    def _round_up_bytes(self, size):
        """
        When requesting a certain number of bytes, we want to round up
        to the nearest block boundary to always fetch a little more
        to make subsequent reads faster.
        """
        return int((math.ceil(
            float(size) / self._blksize) + 1) * self._blksize)

    def read(self, size=-1):
        # Adjust size so it doesn't go beyond the end of the file
        if size < 0 or self._pos + size > self._size:
            size = self._size - self._pos

        if size == 0:
            return b''

        new_pos = self._pos + size

        if (self._pos >= self._buffer_start and
            new_pos <= self._buffer_end):
            # The request can be met entirely with the existing buffer
            result = self._buffer[
                self._pos - self._buffer_start:
                new_pos - self._buffer_start]
            self._pos = new_pos
            return result
        elif (self._pos >= self._buffer_start and
              self._pos < self._buffer_end):
            # The request contains the buffer, and some new content
            # immediately following
            nbytes = new_pos - self._buffer_end
            nbytes = self._round_up_bytes(nbytes)
            end = min(self._buffer_end + nbytes, self._size)
            new_content = self._get_range(self._buffer_end, end).read()
            result = (self._buffer[self._pos - self._buffer_start:] +
                      new_content[:new_pos - self._buffer_end])
            self._buffer = new_content
            self._buffer_start = self._buffer_end
            self._buffer_end = self._buffer_start + len(new_content)
            self._pos = new_pos
            return result
        else:
            # The request doesn't contain the buffer.  We don't deal
            # with the case where the request includes content before
            # the buffer and the buffer itself because such small
            # rewinds are not really done in pyfinf.
            nbytes = self._round_up_bytes(size)
            end = min(self._pos + nbytes, self._size)
            new_content = self._get_range(self._pos, end).read()
            self._buffer = new_content
            self._buffer_start = self._pos
            self._buffer_end = end
            self._pos = new_pos
            return new_content[:size]

    def seek(self, offset, whence=0):
        if whence == os.SEEK_SET:
            self._pos = offset
        elif whence == os.SEEK_CUR:
            self._pos += offset
        elif whence == os.SEEK_END:
            self._pos = self._size - offset

    def tell(self):
        return self._pos

    def read_into_array(self, size):
        if self._pos + size > self._size:
            raise IOError("Read past end of file.")

        new_pos = self._pos + size

        # If we already have the whole thing in the buffer, use that,
        # otherwise, it's most memory efficient to bypass self.read
        # (which would make a temporary memory buffer), and instead
        # just make a new request and read directly from the file
        # object into the array.
        if (self._pos >= self._buffer_start and
            self._pos + size <= self._buffer_end):
            result = np.frombuffer(self._buffer[
                self._pos - self._buffer_start:
                self._pos + size - self._buffer_start], np.uint8, size)
        else:
            response = self._get_range(
                self._pos, self._pos + size)
            with os.fdopen(response.fileno()) as fd:
                result = np.fromfile(fd, np.uint8, size)

        self._pos = new_pos
        return result


def make_http_connection(init, uri=None):
    """
    Creates a HTTPConnection instance if the HTTP server supports
    Range requests, otherwise falls back to a generic InputStream.
    """
    from astropy.extern.six.moves import http_client

    parsed = urlparse.urlparse(init)
    connection = http_client.HTTPConnection(parsed.netloc)
    connection.connect()

    # We request a range of everything ("0-") just to check if the
    # server understands that header entry.
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
        return InputStream(response, close=True)

    # Since we'll be requesting chunks, we can't read at all with the
    # current request (because we can't abort it), so just close and
    # start over
    size = int(response.getheader('content-length'))
    connection.close()
    connection.connect()
    return HTTPConnection(connection, size, parsed.path, uri or init)


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

    if isinstance(init, (GenericFile, GenericWrapper)):
        if mode not in init.mode:
            raise ValueError(
                "File is opened as '{0}', but '{1}' was requested".format(
                    init.mode, mode))
        return GenericWrapper(init, uri=uri)

    elif isinstance(init, six.string_types):
        parsed = urlparse.urlparse(init)
        if parsed.scheme == 'http':
            if 'w' in mode:
                raise ValueError(
                    "HTTP connections can not be opened for writing")
            return make_http_connection(init, uri=uri)
        elif parsed.scheme in ('', 'file'):
            return RealFile(
                open(parsed.path, mode + 'b'), mode, close=True,
                uri=uri or parsed.path)

    elif isinstance(init, io.BytesIO):
        return MemoryIO(init, mode, uri=uri)

    elif isinstance(init, io.StringIO):
        raise TypeError(
            "io.StringIO objects are not supported.  Use io.BytesIO instead.")

    elif six.PY2 and isinstance(init, file):
        if not mode in init.mode:
            raise ValueError(
                "File is opened as '{0}', but '{1}' was requested".format(
                    init.mode, mode))

        try:
            init.tell()
        except IOError:
            if mode == 'w':
                return OutputStream(init, uri=uri)
            elif mode == 'r':
                return InputStream(init, uri=uri)
            else:
                raise ValueError(
                    "File '{0}' could not be opened in 'rw' mode".format(init))
        else:
            return RealFile(init, mode, uri=uri)

    elif isinstance(init, io.IOBase):
        if sys.version_info[:2] == (2, 6):
            raise ValueError("io.open file objects are not supported on Python 2.6")

        if (('r' in mode and not init.readable()) or
            ('w' in mode and not init.writable())):
            raise ValueError(
                "File is opened as '{0}', but '{1}' was requested".format(
                    init.mode, mode))

        if init.seekable():
            if isinstance(init, (io.BufferedReader, io.BufferedWriter)):
                init = init.detach()
            if isinstance(init, io.RawIOBase):
                return RealFile(init, mode, uri=uri)
            else:
                return MemoryIO(init, mode, uri=uri)
        else:
            if mode == 'w':
                return OutputStream(init, uri=uri)
            elif mode == 'r':
                return InputStream(init, uri=uri)
            else:
                raise ValueError(
                    "File '{0}' could not be opened in 'rw' mode".format(init))

    elif (hasattr(init, 'read') and
          hasattr(init, 'write') and
          hasattr(init, 'seek') and
          hasattr(init, 'tell')):
        return MemoryIO(init, uri=uri)

    elif mode == 'r' and hasattr(init, 'read'):
        return InputStream(init, uri=uri)

    elif mode == 'w' and hasattr(init, 'write'):
        return OutputStream(init, uri=uri)

    raise ValueError("Can't handle '{0}' as a file for mode '{1}'".format(
        init, mode))
