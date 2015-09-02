# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

"""
Utilities for embedded ADSF files in FITS.
"""
import io
import re

import numpy as np

import six

from . import asdf
from . import block
from . import util

try:
    from astropy.io import fits
except ImportError:
    raise ImportError("AsdfInFits requires astropy")


ASDF_EXTENSION_NAME = 'ASDF'

FITS_SOURCE_PREFIX = 'fits:'


class _FitsBlock(object):
    def __init__(self, hdu):
        self._hdu = hdu

    def __repr__(self):
        return '<FitsBlock {0},{1}>'.format(self._hdu.name, self._hdu.ver)

    def __len__(self):
        return self._hdu.data.nbytes

    @property
    def data(self):
        return self._hdu.data

    @property
    def array_storage(self):
        return 'fits'

    def override_byteorder(self, byteorder):
        return 'big'


class _EmbeddedBlockManager(block.BlockManager):
    def __init__(self, hdulist, asdffile):
        self._hdulist = hdulist

        super(_EmbeddedBlockManager, self).__init__(asdffile)

    def get_block(self, source):
        if (isinstance(source, six.string_types) and
            source.startswith(FITS_SOURCE_PREFIX)):
            parts = re.match(
                '((?P<name>[A-Z0-9]+),)?(?P<ver>[0-9]+)',
                source[len(FITS_SOURCE_PREFIX):])
            if parts is not None:
                ver = int(parts.group('ver'))
                if parts.group('name'):
                    pair = (parts.group('name'), ver)
                else:
                    pair = ver
                return _FitsBlock(self._hdulist[pair])
            else:
                raise ValueError("Can not parse source '{0}'".format(source))

        return super(_EmbeddedBlockManager, self).get_block(source)

    def get_source(self, block):
        if isinstance(block, _FitsBlock):
            for i, hdu in enumerate(self._hdulist):
                if hdu is block._hdu:
                    if hdu.name == '':
                        return '{0}{1}'.format(
                            FITS_SOURCE_PREFIX, i)
                    else:
                        return '{0}{1},{2}'.format(
                            FITS_SOURCE_PREFIX, hdu.name, hdu.ver)
            raise ValueError("FITS block seems to have been removed")

        return super(_EmbeddedBlockManager, self).get_source(block)

    def find_or_create_block_for_array(self, arr, ctx):
        from .tags.core import ndarray

        if not isinstance(arr, ndarray.NDArrayType):
            base = util.get_array_base(arr)
            for hdu in self._hdulist:
                if base is hdu.data:
                    return _FitsBlock(hdu)

        return super(
            _EmbeddedBlockManager, self).find_or_create_block_for_array(arr, ctx)


class AsdfInFits(asdf.AsdfFile):
    """
    Embed ASDF tree content in a FITS file.

    The YAML rendering of the tree is stored in a special FITS
    extension with the EXTNAME of ``ASDF``.  Arrays in the ASDF tree
    may refer to binary data in other FITS extensions by setting
    source to a string with the prefix ``fits:`` followed by an
    ``EXTNAME``, ``EXTVER`` pair, e.g. ``fits:SCI,0``.

    Examples
    --------
    Create a FITS file with ASDF structure, based on an existing FITS
    file::

        from astropy.io import fits

        hdulist = fits.HDUList()
        hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='SCI'))
        hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='DQ'))

        tree = {
            'model': {
                'sci': {
                    'data': hdulist['SCI'].data,
                    'wcs': 'WCS info'
                },
                'dq': {
                    'data': hdulist['DQ'].data,
                    'wcs': 'WCS info'
                }
            }
        }

        ff = fits_embed.AsdfInFits(hdulist, tree)
        ff.write_to('test.fits')  # doctest: +SKIP
    """

    def __init__(self, hdulist=None, tree=None, uri=None, extensions=None):
        if hdulist is None:
            hdulist = fits.HDUList()
        super(AsdfInFits, self).__init__(
            tree=tree, uri=uri, extensions=extensions)
        self._blocks = _EmbeddedBlockManager(hdulist, self)
        self._hdulist = hdulist

    def __exit__(self, type, value, traceback):
        super(AsdfInFits, self).__exit__(type, value, traceback)
        self._tree = {}

    def close(self):
        super(AsdfInFits, self).close()
        self._tree = {}

    @classmethod
    def open(cls, hdulist, uri=None, validate_checksums=False, extensions=None):
        self = cls(hdulist, uri=uri, extensions=extensions)

        try:
            asdf_extension = hdulist[ASDF_EXTENSION_NAME]
        except (KeyError, IndexError, AttributeError):
            return self

        buff = io.BytesIO(asdf_extension.data)

        return cls._open_impl(self, buff, uri=uri, mode='r',
                              validate_checksums=validate_checksums)

    def _update_asdf_extension(self, all_array_storage=None,
                               all_array_compression=None,
                               auto_inline=None, pad_blocks=False):
        if self.blocks.streamed_block is not None:
            raise ValueError(
                "Can not save streamed data to ASDF-in-FITS file.")

        buff = io.BytesIO()
        super(AsdfInFits, self).write_to(
            buff, all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            auto_inline=auto_inline, pad_blocks=pad_blocks,
            include_block_index=False)
        array = np.frombuffer(buff.getvalue(), np.uint8)

        try:
            asdf_extension = self._hdulist[ASDF_EXTENSION_NAME]
        except (KeyError, IndexError, AttributeError):
            self._hdulist.append(fits.ImageHDU(array, name=ASDF_EXTENSION_NAME))
        else:
            asdf_extension.data = array

    def write_to(self, filename, all_array_storage=None,
                 all_array_compression=None, auto_inline=None,
                 pad_blocks=False, *args, **kwargs):
        self._update_asdf_extension(
            all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            auto_inline=auto_inline, pad_blocks=pad_blocks)

        self._hdulist.writeto(filename, *args, **kwargs)

    def update(self, all_array_storage=None, all_array_compression=None,
               auto_inline=None, pad_blocks=False):
        self._update_asdf_extension(
            all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            auto_inline=auto_inline, pad_blocks=pad_blocks)
