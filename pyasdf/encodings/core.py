# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io

import numpy as np

from astropy.extern import six
from astropy.utils.misc import InheritDocstrings

from .. import generic_io


class _EncodingMeta(InheritDocstrings):
    """
    A metaclass to handle the registering of encoding types.
    """
    registry = {}
    code_registry = {}

    def __new__(mcls, name, bases, members):
        cls = super(mcls, _EncodingMeta).__new__(mcls, name, bases, members)

        if 'name' in members:
            encoding_name = members['name']
            mcls.registry[encoding_name] = cls
            code = members['code']
            mcls.code_registry[code] = cls

        return cls

    @classmethod
    def get_encoding(cls, encoding):
        return cls.registry[encoding]

    @classmethod
    def has_encoding(cls, encoding):
        return encoding in cls.registry

    @classmethod
    def get_encoding_by_code(cls, code):
        if code not in cls.code_registry:
            raise ValueError("Unknown encoding code '{0}'".format(code))
        return cls.code_registry[code]


@six.add_metaclass(_EncodingMeta)
class Encoding(object):
    """
    Base class for all encodings.
    """
    pass


class BinaryEncoding(Encoding):
    """
    Base class for all binary encodings.
    """
    @classmethod
    def get_encoder(cls):
        """
        Get a binary encoder object.  It is a stateful object with two
        methods:

        - ``encode()``: Encode a possibly partial buffer of data
        - ``flush()``: Called when all data has been sent.  May return
          additional bytes.
        """
        raise NotImplementedError()

    @classmethod
    def get_decoder(cls):
        """
        Get a binary decoder object.  It is a stateful object with two
        methods:

        - ``decode()``: Decode a possibly partial buffer of data.
        - ``flush()``: Called when all data has been sent.  May return
          additional bytes.
        """
        raise NotImplementedError()


class ArrayEncoding(Encoding):
    """
    Base class for all array encodings.
    """
    @classmethod
    def encode_array(cls, fd, array):
        """
        Encode the given ``array`` to the file-like object ``fd``.

        Parameters
        ----------
        fd : generic_io.GenericIO instance

        array : numpy array
        """
        raise NotImplementedError()

    @classmethod
    def decode_array(cls, fd):
        """
        Decode an array by reading from the given stream ``fd``.

        Parameters
        ----------
        fd : generic_io.GenericIO instance
        """
        raise NotImplementedError()


def validate_encoding(encoding):
    """
    Validate a human-friendly encoding specifier, which is a list of
    strings.  Returns a normalized version.
    """
    if isinstance(encoding, six.string_types):
        encoding = [encoding]

    if len(encoding) > 16:
        raise ValueError("May not have more than 16 steps in encoding")

    for i, entry in enumerate(encoding):
        if not _EncodingMeta.has_encoding(entry):
            raise ValueError("Unknown encoding type '{0}'".format(entry))

        subencoding = _EncodingMeta.get_encoding(entry)
        if i > 0 and issubclass(subencoding, ArrayEncoding):
            raise ValueError(
                "Array encodings may only appear in the first position")

    return encoding


def names_to_codes(encoding):
    """
    Convert the human-friendly encoding specifier to the codes used in
    the ASDF file.
    """
    codes = []
    for entry in encoding:
        codes.append(_EncodingMeta.get_encoding(entry).code)
    return b''.join(codes)


def codes_to_names(codes):
    """
    Convert the codes used to specify the encoding in the ASDF file to
    a human-friendly list.
    """
    encoding = []
    for code in codes:
        encoding.append(_EncodingMeta.get_encoding_by_code(code).name)
    return encoding


def encode(fd, array, encoding):
    """
    Encode an array using the given encoding.

    Parameters
    ----------
    fd : GenericIO object
        File to write to.

    array : numpy.ndarray
        The array to write.

    encoding : list of str
        The list of encodings to use.
    """
    subencoding = _EncodingMeta.get_encoding(encoding[0])
    if issubclass(subencoding, ArrayEncoding):
        array_data = io.BytesIO()
        subencoding.encode_array(array_data, array)
        array_data = array_data.getvalue()
        encoding = encoding[1:]
    else:
        array_data = array.data

    if len(encoding) == 0:
        fd.write(array_data)
        return

    encoders = []
    for entry in encoding:
        subencoding = _EncodingMeta.get_encoding(entry)
        encoders.append(subencoding.get_encoder())

    for i in range(0, len(array_data), fd.block_size):
        block = array_data[i:i+fd.block_size]
        for encoder in encoders:
            block = encoder.encode(block)
        fd.write(block)

    while len(encoders):
        block = encoders[0].flush()
        for encoder in encoders[1:]:
            block = encoder.encode(block)
        fd.write(block)
        encoders = encoders[1:]


def encode_to_string(array, encoding):
    """
    Encode an array using the given encoding and return a string
    containing the encoded version.

    Parameters
    ----------
    array : numpy.ndarray
        The array to write.

    encoding : list of str
        The list of encodings to use.
    """
    buff = io.BytesIO()
    encode(generic_io.OutputStream(buff), array, encoding)
    return buff.getvalue()


def encoded_length(array, encoding):
    """
    Encode an array using the given encoding and return a string
    containing the encoded version.

    Parameters
    ----------
    array : numpy.ndarray
        The array to write.

    encoding : list of str
        The list of encodings to use.
    """
    class SizingWriter(generic_io.OutputStream):
        def __init__(self):
            super(SizingWriter, self).__init__(None)
            self.count = 0

        def write(self, b):
            self.count += len(b)

    writer = SizingWriter()
    encode(writer, array, encoding)
    return writer.count


def decode(fd, size, encoding):
    """
    Decode a data buffer back into an array using the given encoding.

    Parameters
    ----------
    fd : GenericIO object
        The file to read from.

    encoding : list of str
        The list of encodings to use.  They will be applied in reverse
        order.
    """
    subencoding = _EncodingMeta.get_encoding(encoding[0])
    if issubclass(subencoding, ArrayEncoding):
        encoding = encoding[1:]
        array_encoding = subencoding
    else:
        array_encoding = None

    decoders = []
    for entry in encoding[::-1]:
        subencoding = _EncodingMeta.get_encoding(entry)
        decoders.append(subencoding.get_decoder())

    buff = io.BytesIO()
    bytes_read = 0
    while bytes_read < size:
        block = fd.read_block()
        bytes_read += len(block)
        if len(block) == 0:
            break
        for decoder in decoders:
            block = decoder.decode(block)
        buff.write(block)

    while len(decoders):
        block = decoders[0].flush()
        for decoder in decoders[1:]:
            block = decoder.decode(block)
        buff.write(block)
        decoders = decoders[1:]

    if array_encoding is not None:
        buff.seek(0)
        return array_encoding.decode_array(buff)
    return np.frombuffer(buff.getvalue(), np.uint8)
