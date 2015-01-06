# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import zlib


from . import core


class ZlibEncoding(core.BinaryBinaryEncoding):
    name = 'zlib'

    @classmethod
    def get_encoder(cls, next_encoder, args):
        class ZlibEncoder(object):
            def __init__(self, next_enc):
                self.compresser = zlib.compressobj()
                self.next_enc = next_enc

            def encode(self, x):
                self.next_enc.encode(self.compresser.compress(x))

            def flush(self):
                self.next_enc.encode(self.compresser.flush())
                self.next_enc.flush()

        return ZlibEncoder(next_encoder)

    @classmethod
    def get_decoder(cls, next_decoder, args):
        class ZlibDecoder(object):
            def __init__(self, next_dec):
                self.decompresser = zlib.decompressobj()
                self.next_dec = next_dec

            def decode(self, x):
                self.next_dec.decode(self.decompresser.decompress(x))

            def flush(self):
                self.next_dec.decode(self.decompresser.flush())
                return self.next_dec.flush()

        return ZlibDecoder(next_decoder)
