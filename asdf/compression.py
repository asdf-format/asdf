import struct

import numpy as np
import warnings

from .exceptions import AsdfWarning


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
    
    builtin_labels = ('zlib', 'bzp2', 'lz4', 'input')
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
    def __init__(self, block_api):
        self._api = block_api

    def compress(self, data):
        output = self._api.compress(data, mode='high_compression')
        header = struct.pack('!I', len(output))
        return header + output


class Lz4Decompressor:
    def __init__(self, block_api):
        self._api = block_api
        self._size = 0
        self._pos = 0
        self._buffer = b''

    def decompress(self, data):
        if not self._size:
            data = self._buffer + data
            if len(data) < 4:
                self._buffer += data
                return b''
            self._size = struct.unpack('!I', data[:4])[0]
            data = data[4:]
            self._buffer = bytearray(self._size)
        if self._pos + len(data) < self._size:
            self._buffer[self._pos:self._pos + len(data)] = data
            self._pos += len(data)
            return b''
        else:
            offset = self._size - self._pos
            self._buffer[self._pos:] = data[:offset]
            data = data[offset:]
            self._size = 0
            self._pos = 0
            output = self._api.decompress(self._buffer)
            self._buffer = b''
            return output + self.decompress(data)


def _get_compressor_from_extensions(compression):
    '''
    Look at the loaded ASDF extensions and see if any of them
    know how to handle this kind of compression.
    Returns None if no match found.
    '''
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    extensions = asdf.config.get_config().extensions
    for ext in extensions:
        for comp in ext.compressors:
            for label in comp.labels:
                if compression == label:
                    return comp
    return None
    

def _get_all_compression_extension_labels():
    '''
    Get the list of compression labels supported via extensions
    '''
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    labels = []
    extensions = asdf.config.get_config().extensions
    for ext in extensions:
        for comp in ext.compressors:
            for label in comp.labels:
                labels += [label]
    return labels
    
    
def _get_decoder(compression):
    ext_comp = _get_compressor_from_extensions(compression)
    
    # Check if we have any options set for this decompressor
    options = asdf.config.get_config().compression_options
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
    ext_comp = _get_compressor_from_extensions(compression)
    
    # Check if we have any options set for this compressor
    options = asdf.config.get_config().compression_options
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
        buffer[i:i+len(decoded)] = decoded
        i += len(decoded)
    
    if hasattr(decoder, '_buffer'):
        assert decoder._buffer is None
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
        Input data will be split into blocks of this size (in bytes) before compression.
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

    # We can have numpy arrays here. While compress() will work with them,
    # it is impossible to split them into fixed size blocks without converting
    # them to bytes.
    if isinstance(data, np.ndarray):
        data = memoryview(data.reshape(-1))

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
    
    if hasattr(encoder, 'asdf_block_size'):
        block_size = asdf_block_size

    if isinstance(data, np.ndarray):
        data = memoryview(data.reshape(-1))

    nelem = block_size // data.itemsize
    l = 0
    for i in range(0, len(data), nelem):
        l += len(encoder.compress(data[i:i+nelem]))
    if hasattr(encoder, "flush"):
        l += len(fd.write(encoder.flush()))
    return l
