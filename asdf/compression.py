import struct
import zlib
import bz2
import types

import numpy as np
import warnings

from .exceptions import AsdfWarning
from .config import get_config


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
    ext_labels = _get_all_compression_extension_labels()
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
    def __init__(self, block_api, mode='high_compression', compression_block_size=1<<22):
        self._api = block_api
        self._mode = mode
        self._compression_block_size = compression_block_size

    def compress(self, data):
        nelem = self._compression_block_size // data.itemsize
        output = b''  # TODO: better way to pre-allocate array without knowing final size?
        for i in range(0,len(data),nelem):
            _output = self._api.compress(data[i:i+nelem], mode=self._mode)
            header = struct.pack('!I', len(_output))
            yield header + _output


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

    def decompress(self, data, out=None):
        bytesout = 0
        data = memoryview(data).cast('c')  # don't copy on slice

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

    
class ZlibCompressor:
    def __init__(self, compression_kwargs=None, decompression_kwargs=None):
        if compression_kwargs is None:
            compression_kwargs = {}
        if decompression_kwargs is None:
            decompression_kwargs = {}
            
        self.compression_kwargs = compression_kwargs.copy()
        self._decompressor = zlib.decompressobj(**decompression_kwargs)
        
    def compress(self, data, out=None):
        comp = zlib.compress(data, **self.compression_kwargs)
        if out is not None:
            out[:len(comp)] = comp
            return len(comp)
        return comp
    
    def decompress(self, data, out=None):
        decomp = self._decompressor.decompress(data)
        if out is not None:
            out[:len(decomp)] = decomp
            return len(decomp)
        return decomp
        
    def flush(self, out=None):
        flushed = self._decompressor.flush()
        if out is not None:
            out[:len(flushed)] = flushed
            return len(flushed)
        return flushed
    
    
class Bzp2Compressor:
    def __init__(self, compression_kwargs=None, decompression_kwargs=None):
        if compression_kwargs is None:
            compression_kwargs = {}
        if decompression_kwargs is None:
            decompression_kwargs = {}
            
        self.compression_kwargs = compression_kwargs.copy()
        self._decompressor = bz2.BZ2Decompressor(**decompression_kwargs)
        
    def compress(self, data, out=None):
        comp = bz2.compress(data, **self.compression_kwargs)
        if out is not None:
            out[:len(comp)] = comp
            return len(comp)
        return comp
    
    def decompress(self, data, out=None):
        decomp = self._decompressor.decompress(data)
        if out is not None:
            out[:len(decomp)] = decomp
            return len(decomp)
        return decomp

        
def _get_compressor_from_extensions(compression, return_extension=False):
    '''
    Look at the loaded ASDF extensions and return the first one (if any)
    that can handle this type of compression.
    `return_extension` can be used to return corresponding extension for bookeeping purposes.
    Returns None if no match found.
    '''
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    extensions = get_config().extensions

    for ext in extensions:
        for comp in ext.compressors:
            # TODO: slightly unfortunate to have to construct the object to get the labels
            for label in comp().labels:
                if compression == label:
                    if return_extension:
                        return comp,ext
                    else:
                        return comp
    return None


def _get_all_compression_extension_labels():
    '''
    Get the list of compression labels supported via extensions
    '''
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    labels = []
    extensions = get_config().extensions
    for ext in extensions:
        for comp in ext.compressors:
            # TODO: slightly unfortunate to have to construct the object to get the labels
            for label in comp().labels:
                labels += [label]
    return labels


def _get_decoder(compression):
    ext_comp = _get_compressor_from_extensions(compression)

    # Check if we have any options set for this decompressor
    options = get_config().decompression_options
    options = options.get(compression,{})

    if ext_comp != None:
        # Use an extension before builtins
        return ext_comp(**options)
    elif compression == 'zlib':
        return ZlibCompressor(decompression_kwargs=options)
    elif compression == 'bzp2':
        return Bzp2Compressor(decompression_kwargs=options)
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
    ext_comp = _get_compressor_from_extensions(compression)

    # Check if we have any options set for this compressor
    options = get_config().compression_options
    options = options.get(compression,{})

    if ext_comp != None:
        # Use an extension before builtins
        return ext_comp(**options)
    elif compression == 'zlib':
        return ZlibCompressor(compression_kwargs=options)
    elif compression == 'bzp2':
        return Bzp2Compressor(compression_kwargs=options)
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
        block = memoryview(block).cast('c')

        len_decoded = decoder.decompress(block, out=buffer.data[i:])
        i += len_decoded

    if hasattr(decoder, 'flush'):
        len_decoded = decoder.flush(out=buffer.data[i:])
        i += len_decoded

    if i != data_size:
        raise ValueError("Decompressed data wrong size")

    return buffer


def compress(fd, data, compression):
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
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)

    # Get a contiguous, 1D memoryview of the underlying data, preserving data.itemsize
    # - contiguous: because we may not want to assume that all compressors can handle arbitrary strides
    # - 1D: so that len(data) works, not just data.nbytes
    # - itemsize: should preserve data.itemsize for compressors that want to use the record size
    # - memoryview: don't incur the expense of a memcpy, such as with tobytes()
    data = memoryview(data)
    if not data.contiguous:
        data = memoryview(data.tobytes())  # make a contiguous copy
    data = data.cast('c').cast(data.format)  # we get a 1D array by a cast to byte, then a cast to data.format
    if not data.contiguous:
        # the data will be contiguous by construction, but better safe than sorry!
        raise ValueError(data.contiguous)

    compressed = encoder.compress(data)
    if type(compressed) is types.GeneratorType:
        # Write block by block
        for comp in compressed:
            fd.write(comp)
    else:
        fd.write(compressed)


def get_compressed_size(data, compression):
    """
    Returns the number of bytes required when the given data is
    compressed.

    Parameters
    ----------
    data : buffer

    compression : str
        The type of compression to use.
        
    Returns
    -------
    bytes : int
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)

    # Get a contiguous, 1D memoryview of the underlying data, preserving data.itemsize
    # - contiguous: because we may not want to assume that all compressors can handle arbitrary strides
    # - 1D: so that len(data) works, not just data.nbytes
    # - itemsize: should preserve data.itemsize for compressors that want to use the record size
    # - memoryview: don't incur the expense of a memcpy, such as with tobytes()
    data = memoryview(data)
    if not data.contiguous:
        data = memoryview(data.tobytes())  # make a contiguous copy
    data = data.cast('c').cast(data.format)  # we get a 1D array by a cast to byte, then a cast to data.format
    if not data.contiguous:
        # the data will be contiguous by construction, but better safe than sorry!
        raise ValueError(data.contiguous)

    compressed = encoder.compress(data)
    l = 0
    if type(compressed) is types.GeneratorType:
        # Write block by block
        for comp in compressed:
            l += len(comp)
    else:
        l += len(compressed)
    return l