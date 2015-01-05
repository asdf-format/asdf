# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import struct

import numpy as np

from . import core


END_TOKEN = 0xffffffffffffffff


class SimpleSparseEncoding(core.ArrayEncoding):
    name = 'sparse'
    code = b's'

    @classmethod
    def encode_array(self, fd, array):
        view = array.view(np.uint8).flatten()
        fd.write(struct.pack(b'>Q', len(view)))
        for i, x in enumerate(view):
            if x != 0:
                fd.write(struct.pack(b'>Q', (i << 8) | x))
        fd.write(struct.pack(b'>Q', END_TOKEN))

    @classmethod
    def decode_array(self, fd):
        size, = struct.unpack(b'>Q', fd.read(8))
        array = np.zeros(size, dtype=np.uint8)
        while True:
            chunk = fd.read(8)
            value, = struct.unpack(b'>Q', chunk)
            if value == END_TOKEN:
                break
            location = value >> 8
            value = value & 0xff
            array[location] = value
        return array
