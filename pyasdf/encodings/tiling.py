# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

from astropy.extern.six.moves import xrange

from . import core


def _iter_tiles(array, tile):
    """
    Iterate over tiles of shape `tile` in an ndarray.
    """
    def recurse(array, axis):
        if axis >= len(tile):
            yield array
        else:
            for i in xrange(0, array.shape[axis], tile[axis]):
                s = [slice(None)] * array.ndim
                s[axis] = slice(i, i + tile[axis])
                for subarray in recurse(array[s], axis + 1):
                    yield subarray

    for subarray in recurse(array, 0):
        yield subarray


def _get_n_tiles(array, tile):
    tile = list(tile)
    while len(tile) < array.ndim:
        tile.append(1)
    return int(np.prod(
        np.ceil(
            np.array(array.shape, np.float64) / np.array(tile, np.float64))))


class TilingEncoding(core.ArrayArrayEncoding):
    name = 'tile'

    @classmethod
    def validate_args(self, args):
        if 'shape' not in args:
            raise ValueError("'tile' encoding must have 'shape' argument")
        for i in args['shape']:
            try:
                i = int(i)
            except:
                raise ValueError(
                    "'shape' must be sequence of integers. "
                    "Got '{0}'".format(i))
            if i < 0:
                raise ValueError(
                    "'shape' must be sequence of positive integers. "
                    "Got '{0}'".format(i))

        return args

    @classmethod
    def fix_args(self, array, args):
        args['original_shape'] = list(array.shape)
        args['item_size'] = array.itemsize
        return args

    @classmethod
    def get_encoder(cls, next_encoder, args):
        class TilingEncoder(object):
            def __init__(self, next_enc):
                self.next_enc = next_enc

                self.tile_size = args.get('shape', ())

            def encode(self, x):
                ntiles = _get_n_tiles(x, self.tile_size)
                tiled = np.empty([ntiles] + list(self.tile_size), x.dtype)
                for i, subarray in enumerate(_iter_tiles(x, self.tile_size)):
                    if subarray.shape != self.tile_size:
                        subarray = subarray.copy()
                        subarray.resize(self.tile_size)
                    tiled[i][...] = subarray
                self.next_enc.encode(tiled)

            def flush(self):
                self.next_enc.flush()

        return TilingEncoder(next_encoder)

    @classmethod
    def get_decoder(cls, next_decoder, args):
        class TilingDecoder(object):
            def __init__(self, next_dec):
                self.next_dec = next_dec

                self.item_size = args['item_size']
                self.tile_shape = tuple(args.get('shape', []))
                self.original_shape = tuple(
                    args['original_shape'] + [self.item_size])

            def decode(self, x):
                untiled = np.empty(self.original_shape, np.uint8)
                tile_size = np.prod(self.tile_shape) * self.item_size
                full_tile_shape = tuple(list(self.tile_shape) + [self.item_size])

                index = 0
                for subarray in _iter_tiles(untiled, self.tile_shape):
                    if subarray.shape != full_tile_shape:
                        tmp = np.empty(full_tile_shape, np.uint8)
                        tmp.flat[...] = x[index:index+tile_size]
                        s = tuple(slice(0, x) for x in subarray.shape)
                        subarray.flat[...] = tmp[s].flat
                    else:
                        subarray.flat[...] = x[index:index+tile_size]
                    index += tile_size
                self.next_dec.decode(untiled)

            def flush(self):
                return self.next_dec.flush()

        return TilingDecoder(next_decoder)
