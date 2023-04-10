import hashlib
import io
import struct

from asdf import compression as mcompression
from asdf import constants, generic_io, util


class Block:
    """
    Represents a single block in a ASDF file.  This is an
    implementation detail and should not be instantiated directly.
    Instead, should only be created through the `BlockManager`.
    """

    _header = util.BinaryStruct(
        [
            ("flags", "I"),
            ("compression", "4s"),
            ("allocated_size", "Q"),
            ("used_size", "Q"),
            ("data_size", "Q"),
            ("checksum", "16s"),
        ],
    )

    def __init__(self, data=None, uri=None, array_storage="internal", memmap=True, lazy_load=True, data_callback=None):
        self._data_callback = data_callback
        if self._data_callback is not None and data is not None:
            msg = "Block.__init__ cannot contain non-None data and a non-None data_callback"
            raise ValueError(msg)
        self._data = data
        self._uri = uri
        self._array_storage = array_storage

        self._fd = None
        self._offset = None
        self._input_compression = None
        self._output_compression = "input"
        self._output_compression_kwargs = {}
        self._checksum = None
        self._should_memmap = memmap
        self._memmapped = False
        self._lazy_load = lazy_load

        self.update_size()
        self._allocated = self._size

    def __repr__(self):
        return "<Block {} off: {} alc: {} size: {}>".format(
            self._array_storage[:3],
            self._offset,
            self._allocated,
            self._size,
        )

    def __len__(self):
        return self._size

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset

    @property
    def allocated(self):
        return self._allocated

    @allocated.setter
    def allocated(self, allocated):
        self._allocated = allocated

    @property
    def header_size(self):
        return self._header.size + constants.BLOCK_HEADER_BOILERPLATE_SIZE

    @property
    def data_offset(self):
        return self._offset + self.header_size

    @property
    def size(self):
        return self._size + self.header_size

    @property
    def end_offset(self):
        """
        The offset of the end of the allocated space for the block,
        and where the next block should begin.
        """
        return self.offset + self.header_size + self.allocated

    @property
    def array_storage(self):
        return self._array_storage

    @property
    def input_compression(self):
        """
        The compression codec used to read the block.
        """
        return self._input_compression

    @input_compression.setter
    def input_compression(self, compression):
        self._input_compression = mcompression.validate(compression)

    @property
    def output_compression(self):
        """
        The compression codec used to write the block.
        :return:
        """
        if self._output_compression == "input":
            return self._input_compression
        return self._output_compression

    @output_compression.setter
    def output_compression(self, compression):
        self._output_compression = mcompression.validate(compression)

    @property
    def output_compression_kwargs(self):
        """
        The configuration options to the Compressor constructor
        used to write the block.
        :return:
        """
        return self._output_compression_kwargs

    @output_compression_kwargs.setter
    def output_compression_kwargs(self, config):
        if config is None:
            config = {}
        self._output_compression_kwargs = config.copy()

    @property
    def checksum(self):
        return self._checksum

    def _set_checksum(self, checksum):
        if checksum == b"\0" * 16:
            self._checksum = None
        else:
            self._checksum = checksum

    def _calculate_checksum(self, array):
        # The following line is safe because we're only using
        # the MD5 as a checksum.
        m = hashlib.new("md5")  # noqa: S324
        m.update(array)
        return m.digest()

    def validate_checksum(self):
        """
        Validate the content of the block against the current checksum.

        Returns
        -------
        valid : bool
            `True` if the content is valid against the current
            checksum or there is no current checksum.  Otherwise,
            `False`.
        """
        if self._checksum:
            checksum = self._calculate_checksum(self._flattened_data)
            if checksum != self._checksum:
                return False
        return True

    def update_checksum(self):
        """
        Update the checksum based on the current data contents.
        """
        self._checksum = self._calculate_checksum(self._flattened_data)

    def update_size(self):
        """
        Recalculate the on-disk size of the block.  This causes any
        compression steps to run.  It should only be called when
        updating the file in-place, otherwise the work is redundant.
        """
        if self._data is not None:
            data = self._flattened_data
            self._data_size = data.nbytes

            if not self.output_compression:
                self._size = self._data_size
            else:
                self._size = mcompression.get_compressed_size(
                    data,
                    self.output_compression,
                    config=self.output_compression_kwargs,
                )
        else:
            self._data_size = self._size = 0

    def read(self, fd, past_magic=False, validate_checksum=False):
        """
        Read a Block from the given Python file-like object.

        If the file is seekable and lazy_load is True, the reading
        or memmapping of the actual data is postponed until an array
        requests it.  If the file is a stream or lazy_load is False,
        the data will be read into memory immediately.

        As Block is used for reading, writing, configuring and
        managing data there are circumstances where read should
        not be used. For instance, if a data_callback is defined
        a call to read would override the data corresponding to a
        block and conflict with the use of the data_callback. To
        signify this conflict, a RuntimeError is raised if read
        is called on a block with a defined data_callback.

        Parameters
        ----------
        fd : GenericFile

        past_magic : bool, optional
            If `True`, the file position is immediately after the
            block magic token.  If `False` (default), the file
            position is exactly at the beginning of the block magic
            token.

        validate_checksum : bool, optional
            If `True`, validate the data against the checksum, and
            raise a `ValueError` if the data doesn't match.

        Raises
        ------

        RuntimeError
            Read was called on a block with a defined data_callback.

        ValueError
            The read file contains invalid data.
        """
        if self._data_callback is not None:
            msg = "read called on a Block with a data_callback"
            raise RuntimeError(msg)
        offset = None
        if fd.seekable():
            offset = fd.tell()

        if not past_magic:
            buff = fd.read(len(constants.BLOCK_MAGIC))
            if len(buff) < 4:
                return None

            if buff not in (constants.BLOCK_MAGIC, constants.INDEX_HEADER[: len(buff)]):
                msg = (
                    "Bad magic number in block. "
                    "This may indicate an internal inconsistency about the "
                    "sizes of the blocks in the file."
                )
                raise ValueError(msg)

            if buff == constants.INDEX_HEADER[: len(buff)]:
                return None

        elif offset is not None:
            offset -= 4

        buff = fd.read(2)
        (header_size,) = struct.unpack(b">H", buff)
        if header_size < self._header.size:
            msg = f"Header size must be >= {self._header.size}"
            raise ValueError(msg)

        buff = fd.read(header_size)
        header = self._header.unpack(buff)

        # This is used by the documentation system, but nowhere else.
        self._flags = header["flags"]
        self._set_checksum(header["checksum"])

        try:
            self.input_compression = header["compression"]
        except ValueError:
            raise  # TODO: hint extension?

        if self.input_compression is None and header["used_size"] != header["data_size"]:
            msg = "used_size and data_size must be equal when no compression is used."
            raise ValueError(msg)

        if header["flags"] & constants.BLOCK_FLAG_STREAMED and self.input_compression is not None:
            msg = "Compression set on a streamed block."
            raise ValueError(msg)

        if fd.seekable():
            # If the file is seekable, we can delay reading the actual
            # data until later.
            self._fd = fd
            self._offset = offset
            self._header_size = header_size
            if header["flags"] & constants.BLOCK_FLAG_STREAMED:
                # Support streaming blocks
                self._array_storage = "streamed"
                if self._lazy_load:
                    fd.fast_forward(-1)
                    self._data_size = self._size = self._allocated = (fd.tell() - self.data_offset) + 1
                else:
                    self._data = fd.read_into_array(-1)
                    self._data_size = self._size = self._allocated = len(self._data)
            else:
                self._allocated = header["allocated_size"]
                self._size = header["used_size"]
                self._data_size = header["data_size"]
                if self._lazy_load:
                    fd.fast_forward(self._allocated)
                else:
                    curpos = fd.tell()
                    self._memmap_data()
                    fd.seek(curpos)
                    if not self._memmapped:
                        self._data = self._read_data(fd, self._size, self._data_size)
                        fd.fast_forward(self._allocated - self._size)
                    else:
                        fd.fast_forward(self._allocated)
        else:
            # If the file is a stream, we need to get the data now.
            if header["flags"] & constants.BLOCK_FLAG_STREAMED:
                # Support streaming blocks
                self._array_storage = "streamed"
                self._data = fd.read_into_array(-1)
                self._data_size = self._size = self._allocated = len(self._data)
            else:
                self._allocated = header["allocated_size"]
                self._size = header["used_size"]
                self._data_size = header["data_size"]
                self._data = self._read_data(fd, self._size, self._data_size)
                fd.fast_forward(self._allocated - self._size)
            fd.close()

        if validate_checksum and not self.validate_checksum():
            msg = f"Block at {self._offset} does not match given checksum"
            raise ValueError(msg)

        return self

    def _read_data(self, fd, used_size, data_size):
        """
        Read the block data from a file.
        """
        if not self.input_compression:
            return fd.read_into_array(used_size)

        return mcompression.decompress(fd, used_size, data_size, self.input_compression)

    def _memmap_data(self):
        """
        Memory map the block data from the file.
        """
        memmap = self._fd.can_memmap() and not self.input_compression
        if self._should_memmap and memmap:
            self._data = self._fd.memmap_array(self.data_offset, self._size)
            self._memmapped = True

    @property
    def _flattened_data(self):
        """
        Retrieve flattened data suitable for writing.

        Returns
        -------
        np.ndarray
            1D contiguous array.
        """
        data = self.data

        # 'K' order flattens the array in the order that elements
        # occur in memory, except axes with negative strides which
        # are reversed.  That is a problem for base arrays with
        # negative strides and is an outstanding bug in this library.
        return data.ravel(order="K")

    def write(self, fd):
        """
        Write an internal block to the given Python file-like object.
        """
        self._header_size = self._header.size

        if self._data_callback is not None:
            self._data = self._data_callback()
            data = self._flattened_data
            self.update_size()
            self._data = None
            self._allocated = self._size
        else:
            data = self._flattened_data if self._data is not None else None

        flags = 0
        data_size = used_size = allocated_size = 0
        if self._array_storage == "streamed":
            flags |= constants.BLOCK_FLAG_STREAMED
        elif data is not None:
            self._checksum = self._calculate_checksum(data)
            data_size = data.nbytes
            if not fd.seekable() and self.output_compression:
                buff = io.BytesIO()
                mcompression.compress(buff, data, self.output_compression, config=self.output_compression_kwargs)
                self.allocated = self._size = buff.tell()
            allocated_size = self.allocated
            used_size = self._size
        self.input_compression = self.output_compression

        if allocated_size < used_size:
            msg = f"Block used size {used_size} larger than allocated size {allocated_size}"
            raise RuntimeError(msg)

        checksum = self.checksum if self.checksum is not None else b"\x00" * 16

        fd.write(constants.BLOCK_MAGIC)
        fd.write(struct.pack(b">H", self._header_size))
        fd.write(
            self._header.pack(
                flags=flags,
                compression=mcompression.to_compression_header(self.output_compression),
                allocated_size=allocated_size,
                used_size=used_size,
                data_size=data_size,
                checksum=checksum,
            ),
        )

        if data is not None:
            if self.output_compression:
                if not fd.seekable():
                    fd.write(buff.getvalue())
                else:
                    # If the file is seekable, we write the
                    # compressed data directly to it, then go back
                    # and write the resulting size in the block
                    # header.
                    start = fd.tell()
                    mcompression.compress(fd, data, self.output_compression, config=self.output_compression_kwargs)
                    end = fd.tell()
                    self.allocated = self._size = end - start
                    fd.seek(self.offset + 6)
                    self._header.update(fd, allocated_size=self.allocated, used_size=self._size)
                    fd.seek(end)
            else:
                if used_size != data_size:
                    msg = f"Block used size {used_size} is not equal to the data size {data_size}"
                    raise RuntimeError(msg)
                fd.write_array(data)

    @property
    def data(self):
        """
        Get the data for the block, as a numpy array.
        """
        if self._data is not None:
            return self._data
        if self._data_callback is not None:
            return self._data_callback()
        if self._fd.is_closed():
            msg = "ASDF file has already been closed. Can not get the data."
            raise OSError(msg)

        # Be nice and reset the file position after we're done
        curpos = self._fd.tell()
        try:
            self._memmap_data()
            if not self._memmapped:
                self._fd.seek(self.data_offset)
                self._data = self._read_data(self._fd, self._size, self._data_size)
        finally:
            self._fd.seek(curpos)
        return self._data

    def close(self):
        self._data = None

    def generate_read_data_callback(self):
        """Used in SerializationContext.get_block_data_callback"""

        def callback():
            return self.data

        return callback


class UnloadedBlock:
    """
    Represents an indexed, but not yet loaded, internal block.  All
    that is known about it is its offset.  It converts itself to a
    full-fledged block whenever the underlying data or more detail is
    requested.
    """

    def __init__(self, fd, offset, memmap=True, lazy_load=True):
        self._fd = fd
        self._offset = offset
        self._data = None
        self._uri = None
        self._array_storage = "internal"
        self._input_compression = None
        self._output_compression = "input"
        self._output_compression_kwargs = {}
        self._checksum = None
        self._should_memmap = memmap
        self._memmapped = False
        self._lazy_load = lazy_load
        self._data_callback = None

    def __len__(self):
        self.load()
        return len(self)

    def close(self):
        pass

    @property
    def array_storage(self):
        return "internal"

    @property
    def offset(self):
        return self._offset

    def __getattr__(self, attr):
        self.load()
        return getattr(self, attr)

    def load(self):
        self._fd.seek(self._offset, generic_io.SEEK_SET)
        self.__class__ = Block
        self.read(self._fd)
