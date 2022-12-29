import copy
import hashlib
import io
import struct
import weakref

import numpy as np

from . import compression as mcompression
from . import constants, generic_io, util

BLOCK_HEADER = util.BinaryStruct(
    [
        ("flags", "I"),
        ("compression", "4s"),
        ("allocated_size", "Q"),
        ("used_size", "Q"),
        ("data_size", "Q"),
        ("checksum", "16s"),
    ]
)


class BlockConfig:
    """
    Store defined configuration of a block. This configuration
    is defined by the user (or defaults) and will be used when reading
    and writing a block.
    """

    def __init__(
        self,
        lazy_load=True,
        memmap=True,
        cache_data=True,
        stream=False,
        validate_checksum=False,
        output_compression=None,
        output_compression_kwargs=None,
        padding=False,
    ):
        self.lazy_load = lazy_load
        self.memmap = memmap
        self.cache_data = cache_data
        self.stream = stream
        self.validate_checksum = validate_checksum
        self.padding = padding
        self.output_compression = output_compression
        if output_compression_kwargs is None:
            self.output_compression_kwargs = {}
        else:
            self.output_compression_kwargs = output_compression_kwargs


class BlockState:
    def __init__(self, header, data, config):
        self.header = header
        self.config = config
        self.data = data

    @property
    def data(self):
        if callable(self._data):  # data is lazy loaded
            if self.config.cache_data:
                # cache the data here so it's only read once
                self._data = self._data()
                return self._data
            else:
                # do not cache the data
                return self._data()
        else:
            # we have pre-cached or non-lazy loaded data
            return self._data

    @data.setter
    def data(self, new_value):
        self._data = new_value


def calculate_block_checksum(data):
    if data.ndim > 1:
        data = data.ravel(order="K")
    # The following line is safe because we're only using
    # the MD5 as a checksum.
    m = hashlib.new("md5")  # nosec
    m.update(data)
    return m.digest()


def validate_block_header(header):
    compression = mcompression.validate(header["compression"])
    if header["flags"] & constants.BLOCK_FLAG_STREAMED:
        if compression is not None:
            raise ValueError("Compression set on a streamed block.")
    else:
        if compression is None:
            if header["used_size"] != header["data_size"]:
                raise ValueError("used_size and data_size must be equal when no compression is used.")
    return header


def read_block_header(fd, config, offset=None, past_magic=False):
    if offset is not None:
        fd.seek(offset)

    # first, see if we are at the BLOCK_MAGIC
    if not past_magic:
        buff = fd.read(4)
        # TODO this would be better managed in the block manager but to match the old block
        # behavior we will check the header and return None here
        if len(buff) < 4 or buff == constants.INDEX_HEADER[:4]:
            return None
        if buff != constants.BLOCK_MAGIC:
            raise ValueError(f"Invalid bytes {buff!r}, expected {constants.BLOCK_MAGIC!r}")
    buff = fd.read(2)

    # then read the header size
    header_size = struct.unpack(b">H", buff)[0]
    if header_size < BLOCK_HEADER.size:
        raise ValueError(f"Header size must be >= {BLOCK_HEADER.size}")

    header = BLOCK_HEADER.unpack(fd.read(header_size))
    return validate_block_header(header)


def read_block_data(fd, header, config, offset=None):
    if fd.seekable():
        if offset is not None:
            fd.seek(offset)
        else:
            offset = fd.tell()

    # if we're 'lazy loading' data, return a function
    # that when evaluated will return the data
    # we need to add this here in to capture the offset and fd
    if config.lazy_load and fd.seekable():

        def wrap_read(fd, header, config, offset):
            # only keep a weak reference to the fd
            fd_ref = weakref.proxy(fd)
            # copy the header dictionary
            header_copy = copy.deepcopy(header)
            # copy and modify the config to keep all settings except lazy_load
            config_copy = copy.deepcopy(config)
            config_copy.lazy_load = False

            def read():
                # record and reset file position as this could occur during an update
                previous_position = fd_ref.tell()
                data = read_block_data(fd_ref, header_copy, config_copy, offset)
                fd_ref.seek(previous_position)
                return data

            return read

        # if this is a streamed block, fast forward to the end of the file
        if header["flags"] & constants.BLOCK_FLAG_STREAMED:
            fd.fast_forward(-1)
        else:
            fd.fast_forward(header["allocated_size"])
        return wrap_read(fd, header, config, offset)

    # otherwise we need to load and possibly decompress the data
    # read the raw bytes
    if header["flags"] & constants.BLOCK_FLAG_STREAMED:
        used_size = -1
    else:
        used_size = header["used_size"]

    # if no compression, just read data
    compression = mcompression.validate(header["compression"])
    if compression:
        # TODO the old code ignored memmapping for compressed data
        # if config.memmap:
        #    raise ValueError("Cannot memmap compressed block")
        data = mcompression.decompress(fd, used_size, header["data_size"], compression)
    else:
        if config.memmap and fd.can_memmap():
            data = fd.memmap_array(offset, used_size)
            fd.fast_forward(header["allocated_size"])
        else:
            data = fd.read_into_array(used_size)
            fd.fast_forward(header["allocated_size"] - header["used_size"])

    if config.validate_checksum:
        if calculate_block_checksum(data) != header["checksum"]:
            raise ValueError(f"Block at {offset} does not match given checksum")

    return data


def read_block(fd, config, offset=None, past_magic=False):
    if offset is None and fd.seekable():
        offset = fd.tell()
    header = read_block_header(fd, config, offset, past_magic)
    if header is None:
        return None
    data = read_block_data(fd, header, config)
    block_state = BlockState(header, data, config)
    return block_state


def write_block(fd, data, config, offset=None, **header_kwargs):
    if offset is not None:
        if fd.seekable():
            fd.seek(offset)
        else:
            raise ValueError("write_block received offset for non-seekable file")
    if data.ndim != 1 or data.dtype != "uint8":
        raise ValueError("Data must be of ndim==1 and dtype==uint8")

    # if this is a streamed block, set the streamed header flag
    if config.stream:
        header_kwargs["flags"] = header_kwargs.get("flags", 0) | constants.BLOCK_FLAG_STREAMED

    # data size
    if config.stream:
        header_kwargs["data_size"] = 0
    else:
        header_kwargs["data_size"] = data.nbytes

    # checksum
    if config.stream:
        header_kwargs["checksum"] = b"\0" * 16
    else:
        header_kwargs["checksum"] = calculate_block_checksum(data)

    # compression
    if config.output_compression is not None:
        compression = config.output_compression
    else:
        compression = None
    compression = header_kwargs.get("compression", compression)
    header_kwargs["compression"] = mcompression.to_compression_header(compression)

    # used size
    if compression is None:
        used_size = header_kwargs["data_size"]
    else:
        buff = io.BytesIO()
        mcompression.compress(buff, data, header_kwargs["compression"], config=config.output_compression_kwargs)
        used_size = buff.tell()
    if config.stream:
        header_kwargs["used_size"] = 0
    else:
        header_kwargs["used_size"] = used_size

    # allocated size
    if config.stream:
        header_kwargs["allocated_size"] = 0
    else:
        padding = util.calculate_padding(used_size, config.padding, fd.block_size)
        header_kwargs["allocated_size"] = header_kwargs.get("allocated_size", used_size + padding)
    if header_kwargs["allocated_size"] < header_kwargs["used_size"]:
        raise RuntimeError(
            f"Block used size {header_kwargs['used_size']} larger than "
            f"allocated size {header_kwargs['allocated_size']}"
        )

    fd.write(constants.BLOCK_MAGIC)
    write_header = BLOCK_HEADER.pack(**header_kwargs)
    fd.write(struct.pack(b">H", len(write_header)))
    fd.write(write_header)
    if compression:
        fd.write(buff.getvalue())
    else:
        fd.write_array(data)
    # TODO avoid packing/unpacking this
    write_header = BLOCK_HEADER.unpack(write_header)
    fd.fast_forward(write_header["allocated_size"] - write_header["used_size"])
    return write_header


class Block:
    """
    Represents a single block in a ASDF file.  This is an
    implementation detail and should not be instantiated directly.
    Instead, should only be created through the `BlockManager`.
    """

    def __init__(self, data=None, uri=None, array_storage="internal", memmap=True, lazy_load=True, cache_data=True):
        self._data = data
        self._uri = uri
        self._array_storage = array_storage

        self._config = BlockConfig(
            lazy_load=lazy_load,
            cache_data=cache_data,
            memmap=memmap,
            output_compression="input",
            output_compression_kwargs={},
        )

        self._state = None

        # rather than holding onto the file descriptor, keep track of if it's 'closed'
        self._is_closed = False

        self._offset = None
        self._allocated = None

    def __repr__(self):
        return "<Block {} off: {} alc: {} size: {}>".format(
            self._array_storage[:3], self.offset, self.allocated, len(self)
        )

    @property
    def checksum(self):
        if self._state is None:
            return None
        return self._state.header["checksum"]

    def __len__(self):
        if self._state is None:
            return self._measure_size()
        # streamed blocks have undefined 'used_size'
        if self._state.header["flags"] & constants.BLOCK_FLAG_STREAMED:
            return len(self.data)
        else:
            return self._state.header["used_size"]

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset

    @property
    def allocated(self):
        if self._allocated is not None:
            return self._allocated
        if self._state is None:
            return 0
        if self._state.header["flags"] & constants.BLOCK_FLAG_STREAMED:
            return len(self.data)
        else:
            return self._state.header["allocated_size"]

    @allocated.setter
    def allocated(self, allocated):
        # block manager needs to set allocated when expanding blocks
        # to fill space on an update
        self._allocated = allocated

    @property
    def header_size(self):
        return BLOCK_HEADER.size + constants.BLOCK_HEADER_BOILERPLATE_SIZE

    @property
    def data_offset(self):
        return self._offset + self.header_size

    @property
    def size(self):
        return len(self) + self.header_size

    @property
    def end_offset(self):
        """
        The offset of the end of the allocated space for the block,
        and where the next block should begin.
        """
        return self.offset + self.header_size + self.allocated

    @property
    def trust_data_dtype(self):
        """
        If True, ignore the datatype and byteorder fields from the
        tree and take the data array's dtype at face value.  This
        is used to support blocks stored in FITS files.
        """
        return False

    @property
    def array_storage(self):
        # if self._state is not None and self._state.header['flags'] & constants.BLOCK_FLAG_STREAMED:
        #    return "streamed"
        return self._array_storage

    @property
    def input_compression(self):
        """
        The compression codec used to read the block.
        """
        if self._state is None:
            return None
        return mcompression.validate(self._state.header["compression"])

    @property
    def output_compression(self):
        """
        The compression codec used to write the block.
        :return:
        """
        c = self._config.output_compression
        if c == "input":
            c = self.input_compression
        if isinstance(c, bytes):
            c = c.decode("ascii")
        return c

    @output_compression.setter
    def output_compression(self, compression):
        self._config.output_compression = mcompression.validate(compression)

    @property
    def output_compression_kwargs(self):
        """
        The configuration options to the Compressor constructor
        used to write the block.
        :return:
        """
        return self._config.output_compression_kwargs

    @output_compression_kwargs.setter
    def output_compression_kwargs(self, config):
        if config is None:
            config = {}
        self._config.output_compression_kwargs = config.copy()

    def _measure_size(self):
        """
        Calculate the on-disk size of the block.  This causes any
        compression steps to run.  It should only be called when
        updating the file in-place, otherwise the work is redundant.
        """
        data = self._data
        if data is None:
            return 0
        if not self.output_compression:
            return data.nbytes
        if data.ndim > 1:
            data = data.ravel("K")
        return mcompression.get_compressed_size(data, self.output_compression, config=self.output_compression_kwargs)

    def read(self, fd, past_magic=False, validate_checksum=False):
        """
        Read a Block from the given Python file-like object.

        If the file is seekable and lazy_load is True, the reading
        or memmapping of the actual data is postponed until an array
        requests it.  If the file is a stream or lazy_load is False,
        the data will be read into memory immediately.

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
        """
        config = copy.deepcopy(self._config)
        config.validate_checksum = validate_checksum
        if fd.seekable():
            offset = fd.tell()
            if past_magic:
                offset -= 4
            self.offset = offset
        self._state = read_block(fd, self._config, past_magic=past_magic)
        if self._state is None:
            return None
        if self._state.header["flags"] & constants.BLOCK_FLAG_STREAMED:
            self._array_storage = "streamed"
        return self

    def write(self, fd):
        # TODO the offset needs to be here because the block manager assumes the block
        # will store the write offset
        self.offset = fd.tell()
        data = self.data
        if data is None:
            data = np.array([], dtype="uint8")
        if data.ndim > 1:
            data = data.ravel("K")
        if data.dtype != "uint8":
            data = np.atleast_1d(data).view(dtype="uint8")
        header_kwargs = {}
        if self._allocated is not None:
            header_kwargs["allocated_size"] = self._allocated
        if self._array_storage == "streamed":
            self._config.stream = True
        header_kwargs["compression"] = self.output_compression
        write_header = write_block(fd, data, self._config, **header_kwargs)
        self.allocated = write_header["allocated_size"]

    @property
    def data(self):
        """
        Get the data for the block, as a numpy array.
        """
        if self._data is not None:
            return self._data
        if self._is_closed:
            raise OSError("ASDF file has already been closed. Can not get the data.")
        if self._state is not None:
            return self._state.data
        return None

    def close(self):
        self._data = None
        self._state = None
        self._is_closed = True  # TODO probably better to track this in state


class UnloadedBlock:
    """
    Represents an indexed, but not yet loaded, internal block.  All
    that is known about it is its offset.  It converts itself to a
    full-fledged block whenever the underlying data or more detail is
    requested.
    """

    def __init__(self, fd, offset, memmap=True, lazy_load=True, cache_data=True):
        self._is_closed = False
        self._fd = fd
        self._offset = offset

        self._uri = None
        self._data = None
        self._array_storage = "internal"
        self._state = None
        self._allocated = None
        self._config = BlockConfig(
            lazy_load=lazy_load,
            cache_data=cache_data,
            memmap=memmap,
            output_compression=None,
            output_compression_kwargs={},
        )

    def __len__(self):
        self.load()
        return len(self)

    def close(self):
        self._is_closed = True

    def __getattr__(self, attr):
        self.load()
        return getattr(self, attr)

    def load(self):
        self._fd.seek(self._offset, generic_io.SEEK_SET)
        self.__class__ = Block
        self.read(self._fd)
