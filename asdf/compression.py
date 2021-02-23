import struct

import numpy as np
import warnings

from .exceptions import AsdfWarning
from .config import get_config


DEFAULT_BLOCK_SIZE = 1 << 22  #: Decompressed block size in bytes, 4MiB


def validate(compression):
    """
    Validate the compression string.

    Parameters
    ----------
    compression : str, bytes or None

    Returns
    -------
    compression : str or None
        In canonical form.

    Raises
    ------
    ValueError
    """
    if not compression or compression == b'\0\0\0\0':
        return None

    if isinstance(compression, bytes):
        compression = compression.decode('ascii')

    compression = compression.strip('\0')
    
    builtin_labels = ['zlib', 'bzp2', 'lz4', 'input']
    ext_labels = list(set(_get_all_compression_extension_labels(decompressor=True) +
                          _get_all_compression_extension_labels(decompressor=False)))
    all_labels = ext_labels + builtin_labels
    
    # An extension is allowed to override a builtin compression or another extension,
    # but let's warn the user of this.
    # TODO: is this the desired behavior?
    for i,label in enumerate(all_labels):
        if label in all_labels[i+1:]:
            warnings.warn(f'Found more than one compressor for "{label}"', AsdfWarning)
    
    if compression not in all_labels:
        raise ValueError(
            f"Supported compression types are: {all_labels}, not '{compression}'")

    return compression


class Lz4Compressor:
    def __init__(self, block_api, mode='high_compression'):
        self._api = block_api
        self._mode = mode

    def compress(self, data):
        output = self._api.compress(data, mode=self._mode)
        header = struct.pack('!I', len(output))
        return header + output


class Lz4Decompressor:
    def __init__(self, block_api):
        self._api = block_api
        self._size = 0
        self._pos = 0
        self._partial_len = b''
        self._buffer = None
        
    def __del__(self):
        if self._buffer is not None:
            raise Exception('Found data left in lz4 buffer after decompression')

    def decompress_into(self, data, out):
        bytesout = 0
        data = memoryview(data).cast('c').toreadonly()  # don't copy on slice
        
        while len(data):
            if not self._size:
                # Don't know the (compressed) length of this block yet
                if len(self._partial_len) + len(data) < 4:
                    self._partial_len += data
                    break  # we've exhausted the data
                if self._partial_len:
                    # If we started to fill a len key, finish filling it
                    remaining = 4-len(self._partial_len)
                    if remaining:
                        self._partial_len += data[:remaining]
                        data = data[remaining:]
                    self._size = struct.unpack('!I', self._partial_len)[0]
                    self._partial_len = b''
                else:
                    # Otherwise just read the len key directly
                    self._size = struct.unpack('!I', data[:4])[0]
                    data = data[4:]

            if len(data) < self._size or self._buffer is not None:
                # If we have a partial block, or we're already filling a buffer, use the buffer
                if self._buffer is None:
                    self._buffer = np.empty(self._size, dtype=np.byte)  # use numpy instead of bytearray so we can avoid zero initialization
                    self._pos = 0
                newbytes = min(self._size - self._pos, len(data))  # don't fill past the buffer len!
                self._buffer[self._pos:self._pos+newbytes] = np.frombuffer(data[:newbytes], dtype=np.byte)
                self._pos += newbytes
                data = data[newbytes:]

                if self._pos == self._size:
                    _out = self._api.decompress(self._buffer, return_bytearray=True)
                    out[bytesout:bytesout+len(_out)] = _out
                    bytesout += len(_out)
                    self._buffer = None
                    self._size = 0
            else:
                # We have at least one full block
                _out = self._api.decompress(memoryview(data[:self._size]), return_bytearray=True)
                out[bytesout:bytesout+len(_out)] = _out
                bytesout += len(_out)
                data = data[self._size:]
                self._size = 0

        return bytesout


def _get_compressor_from_extensions(compression, decompressor=False, return_extension=False):
    '''
    Look at the loaded ASDF extensions and return the first one (if any)
    that can handle this type of compression.
    `return_extension` can be used to return corresponding extension for bookeeping purposes.
    Returns None if no match found.
    '''
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    extensions = get_config().extensions
    
    for ext in extensions:
        compressors = ext.decompressors if decompressor else ext.compressors
        for comp in compressors:
            # TODO: slightly unfortunate to have to construct the object to get the labels
            for label in comp().labels:
                if compression == label:
                    if return_extension:
                        return comp,ext
                    else:
                        return comp
    return None
    

def _get_all_compression_extension_labels(decompressor=False):
    '''
    Get the list of compression labels supported via extensions
    '''
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    labels = []
    extensions = get_config().extensions
    for ext in extensions:
        compressors = ext.decompressors if decompressor else ext.compressors
        for comp in compressors:
            # TODO: slightly unfortunate to have to construct the object to get the labels
            for label in comp().labels:
                labels += [label]
    return labels
    
    
def _get_decoder(compression):
    ext_comp = _get_compressor_from_extensions(compression, decompressor=True)
    
    # Check if we have any options set for this decompressor
    options = get_config().decompression_options
    options = options.get(compression,{})
    
    if ext_comp != None:
        # Use an extension before builtins
        return ext_comp(**options)
    elif compression == 'zlib':
        try:
            import zlib
        except ImportError:
            raise ImportError(
                "Your Python does not have the zlib library, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return zlib.decompressobj(**options)
    elif compression == 'bzp2':
        try:
            import bz2
        except ImportError:
            raise ImportError(
                "Your Python does not have the bz2 library, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return bz2.BZ2Decompressor(**options)
    elif compression == 'lz4':
        try:
            import lz4.block
        except ImportError:
            raise ImportError(
                "lz4 library in not installed in your Python environment, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return Lz4Decompressor(lz4.block, **options)
    else:
        raise ValueError(
            "Unknown compression type: '{0}'".format(compression))


def _get_encoder(compression):
    ext_comp = _get_compressor_from_extensions(compression, decompressor=False)
    
    # Check if we have any options set for this compressor
    options = get_config().compression_options
    options = options.get(compression,{})
    
    if ext_comp != None:
        # Use an extension before builtins
        return ext_comp(**options)
    elif compression == 'zlib':
        try:
            import zlib
        except ImportError:
            raise ImportError(
                "Your Python does not have the zlib library, "
                "therefore the block in this ASDF file "
                "can not be compressed.")
        return zlib.compressobj(**options)
    elif compression == 'bzp2':
        try:
            import bz2
        except ImportError:
            raise ImportError(
                "Your Python does not have the bz2 library, "
                "therefore the block in this ASDF file "
                "can not be compressed.")
        return bz2.BZ2Compressor(**options)
    elif compression == 'lz4':
        try:
            import lz4.block
        except ImportError:
            raise ImportError(
                "lz4 library in not installed in your Python environment, "
                "therefore the block in this ASDF file "
                "can not be compressed.")
        return Lz4Compressor(lz4.block, **options)
    else:
        raise ValueError(
            "Unknown compression type: '{0}'".format(compression))


def to_compression_header(compression):
    """
    Converts a compression string to the four byte field in a block
    header.
    """
    if not compression:
        return b''

    if isinstance(compression, str):
        return compression.encode('ascii')

    return compression


def decompress(fd, used_size, data_size, compression):
    """
    Decompress binary data in a file

    Parameters
    ----------
    fd : generic_io.GenericIO object
         The file to read the compressed data from.

    used_size : int
         The size of the compressed data

    data_size : int
         The size of the uncompressed data

    compression : str
         The compression type used.

    Returns
    -------
    array : numpy.array
         A flat uint8 containing the decompressed data.
    """
    buffer = np.empty((data_size,), np.uint8)

    compression = validate(compression)
    decoder = _get_decoder(compression)

    i = 0
    for block in fd.read_blocks(used_size):
        # Use a memoryview so decompressors don't trigger a copy on slice
        # The cast ensures 1D and byte-size records
        block = memoryview(block).cast('c').toreadonly()
        
        if hasattr(decoder, 'decompress_into'):
            i += decoder.decompress_into(block, out=buffer[i:])
        else:
            decoded = decoder.decompress(block)
            if i + len(decoded) > data_size:
                raise ValueError("Decompressed data too long")
            buffer.data[i:i+len(decoded)] = decoded
            i += len(decoded)

    if hasattr(decoder, 'flush'):
        decoded = decoder.flush()
        if i + len(decoded) > data_size:
            raise ValueError("Decompressed data too long")
        buffer.data[i:i+len(decoded)] = decoded
        i += len(decoded)
    
    if i != data_size:
        raise ValueError("Decompressed data wrong size")

    return buffer


def compress(fd, data, compression, block_size=None):
    """
    Compress array data and write to a file.

    Parameters
    ----------
    fd : generic_io.GenericIO object
        The file to write to.

    data : buffer
        The buffer of uncompressed data.

    compression : str
        The type of compression to use.

    block_size : int or None, optional
        Input data will be split into blocks of this size (in bytes)
        before compression.
        Default of None will use compression.DEFAULT_BLOCK_SIZE.
        May be overriden with the asdf_block_size option in the
        compression config.
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)
    
    # The encoder is allowed to request a specific ASDF block size,
    # one that is a multiple of its internal block size, for example
    if hasattr(encoder, 'asdf_block_size'):
        if block_size != None:
            warnings.warn(f'The asdf_block_size compression option requests {encoder.asdf_block_size}, '
                      f'which will override the block_size argument of {block_size}',
                      AsdfWarning)
        block_size = asdf_block_size
    else:
        block_size = DEFAULT_BLOCK_SIZE

    # Get a contiguous, 1D, read-only memoryview of the underlying data, preserving data.itemsize
    # - contiguous: because we may not want to assume that all compressors can handle arbitrary strides
    # - 1D: so that len(data) works, not just data.nbytes
    # - itemsize: should preserve data.itemsize for compressors that want to use the record size
    # - memoryview: don't incur the expense of a memcpy, such as with tobytes()
    # - read-only: shouldn't need to modify data!
    data = memoryview(data)
    if not data.contiguous:
        data = memoryview(data.tobytes())  # make a contiguous copy
    data = data.cast('c').cast(data.format).toreadonly()  # we get a 1D array by a cast to byte, then a cast to data.format
    assert data.contiguous  # this is true by construction, but better safe than sorry!

    # Because we are preserving the record size,
    # block_size will only be respected to the nearest multiple
    nelem = block_size // data.itemsize
    for i in range(0, len(data), nelem):
        fd.write(encoder.compress(data[i:i+nelem]))
    if hasattr(encoder, "flush"):
        fd.write(encoder.flush())


def get_compressed_size(data, compression, block_size=DEFAULT_BLOCK_SIZE):
    """
    Returns the number of bytes required when the given data is
    compressed.

    Parameters
    ----------
    data : buffer

    compression : str
        The type of compression to use.

    block_size : int, optional
        Input data will be split into blocks of this size (in bytes) before the compression.

    Returns
    -------
    bytes : int
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)
    
    # The encoder is allowed to request a specific ASDF block size,
    # one that is a multiple of its internal block size, for example
    if hasattr(encoder, 'asdf_block_size'):
        if block_size != None:
            warnings.warn(f'The asdf_block_size compression option requests {encoder.asdf_block_size}, '
                      f'which will override the block_size argument of {block_size}',
                      AsdfWarning)
        block_size = asdf_block_size
    else:
        block_size = DEFAULT_BLOCK_SIZE

    # Get a contiguous, 1D, read-only memoryview of the underlying data, preserving data.itemsize
    # - contiguous: because we may not want to assume that all compressors can handle arbitrary strides
    # - 1D: so that len(data) works, not just data.nbytes
    # - itemsize: should preserve data.itemsize for compressors that want to use the record size
    # - memoryview: don't incur the expense of a memcpy, such as with tobytes()
    # - read-only: shouldn't need to modify data!
    data = memoryview(data)
    if not data.contiguous:
        data = memoryview(data.tobytes())  # make a contiguous copy
    data = data.cast('c').cast(data.format).toreadonly()  # we get a 1D array by a cast to byte, then a cast to data.format
    assert data.contiguous  # this is true by construction, but better safe than sorry!

    # Because we are preserving the record size,
    # block_size will only be respected to the nearest multiple
    nelem = block_size // data.itemsize
    l = 0
    for i in range(0, len(data), nelem):
        l += len(encoder.compress(data[i:i+nelem]))
    if hasattr(encoder, "flush"):
        l += len(encoder.flush())
    return l
