# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import zlib


from . import core


class ZlibEncoding(core.BinaryEncoding):
    name = 'zlib'
    code = b'z'

    @classmethod
    def get_encoder(cls):
        class ZlibEncoder(object):
            def __init__(self):
                self.compresser = zlib.compressobj()

            def encode(self, x):
                return self.compresser.compress(x)

            def flush(self):
                return self.compresser.flush()

        return ZlibEncoder()

    @classmethod
    def get_decoder(cls):
        class ZlibDecoder(object):
            def __init__(self):
                self.decompresser = zlib.decompressobj()
                self._flushed = False

            def decode(self, x):
                return self.decompresser.decompress(x)

            def flush(self):
                return self.decompresser.flush()

        return ZlibDecoder()
