# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import collections
import io

import numpy as np

from astropy.extern import six
from astropy.extern.six.moves import xrange
from astropy.utils.misc import InheritDocstrings

from .. import constants
from .. import generic_io
from .. import yamlutil


# This is the size of the chunks that the encoders/decoders should
# process.  Not sure how much value there is to making this
# user-configurable, so it's just a constant for now.

BLOCK_SIZE = 1 << 16


class _EncodingMeta(InheritDocstrings):
    """
    A metaclass to handle the registering of encoding types.
    """
    registry = {}

    def __new__(mcls, name, bases, members):
        cls = super(mcls, _EncodingMeta).__new__(mcls, name, bases, members)

        if 'name' in members:
            encoding_name = members['name']
            mcls.registry[encoding_name] = cls

        return cls

    @classmethod
    def get_encoding(cls, encoding):
        """
        Get the Encoding subclass for the given encoding name.
        """
        return cls.registry[encoding]

    @classmethod
    def has_encoding(cls, encoding):
        """
        Returns `True` if the given encoding name is in the registry.
        """
        return encoding in cls.registry

    @classmethod
    def get_encodings(cls, encodings):
        """
        Given an ASDF encoding chain, yield a sequence of encoding
        classes to perform the chain.  Normalization and validation
        is also performed.

        Parameters
        ----------
        encodings : list
            ASDF encoding chain specifier

        Returns
        -------
        encodings : generator
            Each entry is an object with the following:

            - ``name``: The name of the encoding
            - ``args``: A dictionary of arguments to the encoding
            - ``cls``: An Encoding subclass corresponding to the encoding
        """
        Entry = collections.namedtuple('Entry', ['name', 'args', 'cls'])

        if isinstance(encodings, six.string_types):
            encodings = [encodings]

        if not len(encodings):
            return

        rep = 'array'

        for i, entry in enumerate(encodings):
            if isinstance(entry, six.string_types):
                encoding_name = entry
                args = {}
            elif len(entry) == 1:
                encoding_name = entry[0]
                args = {}
            else:
                encoding_name, args = entry

            if not cls.has_encoding(encoding_name):
                raise ValueError("Unknown encoding type '{0}'".format(entry))

            encoder = cls.get_encoding(encoding_name)
            if issubclass(encoder, ArrayArrayEncoding):
                if rep == 'binary':
                    raise ValueError(
                        "array-to-array encoding '{0}' appears after binary "
                        "encoding".format(encoding_name))
            elif issubclass(encoder, ArrayBinaryEncoding):
                if rep == 'binary':
                    raise ValueError(
                        "array-to-binary encoding '{0}' appears after binary "
                        "encoding".format(encoding_name))
                rep = 'array'
            elif issubclass(encoder, BinaryBinaryEncoding):
                if rep == 'array':
                    yield Entry('null', {}, NullArrayEncoding)
                rep = 'binary'

            args = encoder.validate_args(args)

            yield Entry(encoding_name, args, encoder)

        if not issubclass(encoder, (ArrayBinaryEncoding, BinaryBinaryEncoding)):
            yield Entry('null', {}, NullArrayEncoding)


@six.add_metaclass(_EncodingMeta)
class Encoding(object):
    """
    Base class for all encodings.
    """
    @classmethod
    def validate_args(cls, args):
        """
        Raises a `ValueError` if any of the arguments are invalid or
        missing.  Returns a normalized version of the `args`.
        """
        return args

    @classmethod
    def fix_args(cls, array, args):
        """
        Adds any additional arguments to allow decoding that need to
        be added during the encoding step.
        """
        return args

    @classmethod
    def get_encoder(cls, next_encoder, args):
        """Get a encoder object for this encoding.

        Parameters
        ----------
        next_encoder : encoder
            The next encoder in the encoding chain.

        args : dict
            A dictionary of arguments for the encoder.

        Returns
        -------
        encoder : encoder
            An object with the following methods:

            - ``encode(x)``:
              - For array-to-array encodings, ``x`` is an array, and a
                new encoded array must be passed to
                ``next_encoder.encode()``.
              - For array-to-binary encodings, ``x`` is an array and a
                `bytes` object containing the encoding of that array
                must be passed to ``next_encoder.encode()``.
              - For binary-to-binary encodings, ``x`` is a `bytes`
                object and an encoded `bytes` object must be passed to
                ``next_encoder.encode()``.  When passing along `bytes`
                object, the stream may be passed in chunks.

            - ``flush()``: Called when encoding is completed.  May
              pass along additional binary data to
              ``next_encoder.encode()``, and then must call
              ``next_encoder.flush()``.
        """
        raise NotImplementedError()

    @classmethod
    def get_decoder(cls, next_decoder, args):
        """
        Get a decoder object for this decoding.

        Parameters
        ----------
        next_decoder : decoder
            The next decoder in the encoding chain.

        args : dict
            A dictionary of arguments for the decoder.

        Returns
        -------
        decoder : decoder
            An object with the following methods:

            - ``decode(x)``:
              - For array-to-array encodings, ``x`` is an array, and a
                new encoded array must be passed to
                ``next_encoder.decode()``.
              - For array-to-binary encodings, ``x`` is a `bytes`
                object, that may represent part of the array.  The
                array should be built from these parts in
                ``decode(x)`` and then returned from ``flush()``.
              - For binary-to-binary encodings, ``x`` is a `bytes`
                object and an decoded `bytes` object must be passed to
                ``next_encoder.decode()``.  When passing along `bytes`
                object, the stream may be passed in chunks.

            - ``flush()``: Called when decoding is completed, and must
              return a completed array, usually as the result of
              calling ``next_decoder.flush()``.
        """
        raise NotImplementedError()


class ArrayBinaryEncoding(Encoding):
    """
    Base class for all array-to-binary encodings.
    """
    pass


class ArrayArrayEncoding(Encoding):
    """
    Base class for all array-to-array encodings.
    """
    pass


class BinaryBinaryEncoding(Encoding):
    """
    Base class for all binary-to-binary encodings.
    """
    pass


class NullArrayEncoding(ArrayBinaryEncoding):
    """
    A simple encoding to go from arrays to their raw in-memory
    representation in binary.
    """

    name = 'null'

    @classmethod
    def get_encoder(cls, next_encoder, args):
        class NullEncoder(object):
            def __init__(self, next_enc):
                self.next_enc = next_enc

            def encode(self, array):
                array_data = array.data

                for i in xrange(0, len(array_data), BLOCK_SIZE):
                    block = array_data[i:i+BLOCK_SIZE]
                    self.next_enc.encode(block)

            def flush(self):
                self.next_enc.flush()

        return NullEncoder(next_encoder)

    @classmethod
    def get_decoder(cls, next_decoder, args):
        class NullDecoder(object):
            def __init__(self, next_dec):
                self.next_dec = next_dec
                self.buff = generic_io.OutputStream(io.BytesIO())

            def decode(self, x):
                self.buff.write(x)

            def flush(self):
                array = np.frombuffer(self.buff._fd.getvalue(), np.uint8)
                self.next_dec.decode(array)
                return self.next_dec.flush()

        return NullDecoder(next_decoder)


class EncodingEndpoint(object):
    """
    The endpoint of an encoding chain that actually writes to the file.
    """
    def __init__(self, fd):
        self.fd = fd

    def encode(self, x):
        self.fd.write(x)

    def flush(self):
        self.fd.flush()


class DecodingEndpoint(object):
    """
    The endpoint of a decoding chain that returns the resulting array.
    """
    def __init__(self):
        pass

    def decode(self, x):
        self.array = x

    def flush(self):
        return self.array


def validate_encoding(encodings, array=None):
    """
    Validate a human-friendly encoding specifier, which is a list of
    strings.  Returns a normalized version suitable for saving as the
    YAML header to an encoded block.
    """
    normalized = []
    for x in _EncodingMeta.get_encodings(encodings):
        if array is not None and hasattr(x.cls, 'fix_args'):
            args = x.cls.fix_args(array, x.args)
        else:
            args = x.args
        if x.name != 'null':
            if len(args):
                normalized.append((x.name, args))
            else:
                normalized.append(x.name)
    return normalized


def encode(fd, array, encoding):
    """
    Encode an array using the given encoding.

    Parameters
    ----------
    fd : file-like object
        File to write to.

    array : numpy.ndarray
        The array to write.

    encoding : ASDF encoding chain
        The list of encodings to use.
    """
    fd = generic_io.get_file(fd, 'w')

    encoding = list(_EncodingMeta.get_encodings(encoding))

    enc = EncodingEndpoint(fd)
    for x in encoding[::-1]:
        enc = x.cls.get_encoder(enc, x.args)

    enc.encode(array)
    enc.flush()


def encode_block(fd, array, encoding):
    """
    Encode a block, including the YAML header describing the encoding.

    Parameters
    ----------
    fd : file-like object
        File to write to.

    array : numpy.ndarray
        The array to write.

    encoding : ASDF encoding chain
        The list of encodings to use.
    """
    fd = generic_io.get_file(fd, 'w')
    encoding = validate_encoding(encoding, array)
    yamlutil.dump(encoding, fd)
    encode(fd, array, encoding)


def encoded_block_length(array, encoding):
    """
    Determine how much space is required to store an encoded version
    of ``array``, including the YAML header describing the encoding
    chain.

    Parameters
    ----------
    array : numpy.ndarray
        The array to write.

    encoding : list of str
        The list of encodings to use.
    """
    class SizingWriter(generic_io.OutputStream):
        def __init__(self):
            super(SizingWriter, self).__init__(io.BytesIO())
            self.count = 0

        def write(self, b):
            self.count += len(b)

        def flush(self):
            pass

    writer = SizingWriter()
    encode_block(writer, array, encoding)
    return writer.count


def decode(fd, encoding, used_size, mem_size=None):
    """
    Decode a binary buffer into an array using the given encoding.

    Parameters
    ----------
    fd : file-like object
        The file to read from.

    encoding : list
        The encoding to use, specified as in the ASDF standard.

    used_size : int
        The number of bytes in the encoding (on disk)

    mem_size : int
        The number of bytes decoded (in memory).

        TODO: This might be useful someday to preallocate the
        resulting array buffer, but currently it is ignored.
    """
    fd = generic_io.get_file(fd, 'r')

    encoding = list(_EncodingMeta.get_encodings(encoding))

    dec = DecodingEndpoint()
    for x in encoding:
        dec = x.cls.get_decoder(dec, x.args)

    for block in fd.read_blocks(used_size):
        dec.decode(block)

    return dec.flush()


def decode_block(fd, used_size, mem_size=None):
    """
    Decode a block, where the encoding is specifed as YAML at the
    beginning of the buffer.

    Parameters
    ----------
    fd : file-like object
        The file to read from.

    used_size : int
        The number of bytes in the encoding (on disk)

    mem_size : int
        The number of bytes decoded (in memory)

        TODO: This might be useful someday to preallocate the
        resulting array buffer, but currently it is ignored.
    """
    fd = generic_io.get_file(fd, 'r')

    encoding_content = fd.read_until(
        constants.YAML_END_MARKER_REGEX, 'End of YAML marker',
        include=True)
    encoding = yamlutil.load(encoding_content)
    encoding = validate_encoding(encoding)

    return decode(fd, encoding, used_size, mem_size), encoding
