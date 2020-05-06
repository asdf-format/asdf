# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


"""
Utilities for embedded ADSF files in FITS.
"""
import io
import re

import numpy as np

from . import asdf
from . import block
from . import util
from . import generic_io

try:
    from astropy.io import fits
    from astropy.io.fits import Column, BinTableHDU
except ImportError:
    raise ImportError("AsdfInFits requires astropy")


ASDF_EXTENSION_NAME = 'ASDF'
FITS_SOURCE_PREFIX = 'fits:'


__all__ = ['AsdfInFits']


class _FitsBlock:
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
    def readonly(self):
        return False

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
        if (isinstance(source, str) and source.startswith(FITS_SOURCE_PREFIX)):
            parts = re.match(
                # All printable ASCII characters are allowed in EXTNAME
                '((?P<name>[ -~]+),)?(?P<ver>[0-9]+)',
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
                if hdu.data is None:
                    continue
                if base is util.get_array_base(hdu.data):
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

    def __init__(self, hdulist=None, tree=None, **kwargs):
        if hdulist is None:
            hdulist = fits.HDUList()
        super(AsdfInFits, self).__init__(tree=tree, **kwargs)
        self._blocks = _EmbeddedBlockManager(hdulist, self)
        self._hdulist = hdulist
        self._close_hdulist = False

    def __exit__(self, type, value, traceback):
        super(AsdfInFits, self).__exit__(type, value, traceback)
        if self._close_hdulist:
            self._hdulist.close()
        self._tree = {}

    def close(self):
        super(AsdfInFits, self).close()
        if self._close_hdulist:
            self._hdulist.close()
        self._tree = {}

    @classmethod
    def open(cls, fd, uri=None, validate_checksums=False, extensions=None,
             ignore_version_mismatch=True, ignore_unrecognized_tag=False,
             strict_extension_check=False, ignore_missing_extensions=False,
             validate_on_read=True):
        """Creates a new AsdfInFits object based on given input data

        Parameters
        ----------
        fd : FITS HDUList instance, URI string, or file-like object
            May be an already opened instance of a FITS HDUList instance,
            string ``file`` or ``http`` URI, or a Python file-like object.

        uri : str, optional
            The URI for this ASDF file.  Used to resolve relative
            references against.  If not provided, will be
            automatically determined from the associated file object,
            if possible and if created from `asdf.open`.

        validate_checksums : bool, optional
            If `True`, validate the blocks against their checksums.
            Requires reading the entire file, so disabled by default.

        extensions : list of AsdfExtension, optional
            A list of extensions to the ASDF to support when reading
            and writing ASDF files.  See `asdf.types.AsdfExtension` for
            more information.

        ignore_version_mismatch : bool, optional
            When `True`, do not raise warnings for mismatched schema versions.

        strict_extension_check : bool, optional
            When `True`, if the given ASDF file contains metadata about the
            extensions used to create it, and if those extensions are not
            installed, opening the file will fail. When `False`, opening a file
            under such conditions will cause only a warning. Defaults to
            `False`.

        ignore_missing_extensions : bool, optional
            When `True`, do not raise warnings when a file is read that
            contains metadata about extensions that are not available. Defaults
            to `False`.

        validate_on_read : bool, optional
            When `True`, validate the newly opened file against tag and custom
            schemas.  Recommended unless the file is already known to be valid.
        """
        return cls._open_impl(fd, uri=uri,
                       validate_checksums=validate_checksums,
                       extensions=extensions,
                       ignore_version_mismatch=ignore_version_mismatch,
                       ignore_unrecognized_tag=ignore_unrecognized_tag,
                       strict_extension_check=strict_extension_check,
                       ignore_missing_extensions=ignore_missing_extensions,
                       validate_on_read=validate_on_read)

    @classmethod
    def _open_impl(cls, fd, uri=None, validate_checksums=False, extensions=None,
             ignore_version_mismatch=True, ignore_unrecognized_tag=False,
             strict_extension_check=False, _extension_metadata=None,
             ignore_missing_extensions=False, validate_on_read=True):

        close_hdulist = False
        if isinstance(fd, fits.hdu.hdulist.HDUList):
            hdulist = fd
        else:
            uri = generic_io.get_uri(fd)
            try:
                hdulist = fits.open(fd)
                # Since we created this HDUList object, we need to be
                # responsible for cleaning up upon close() or __exit__
                close_hdulist = True
            except IOError:
                msg = "Failed to parse given file '{}'. Is it FITS?"
                raise ValueError(msg.format(uri))

        self = cls(hdulist, uri=uri, extensions=extensions,
                   ignore_version_mismatch=ignore_version_mismatch,
                   ignore_unrecognized_tag=ignore_unrecognized_tag)
        if _extension_metadata is not None:
            self._extension_metadata = _extension_metadata

        self._close_hdulist = close_hdulist

        try:
            asdf_extension = hdulist[ASDF_EXTENSION_NAME]
        except (KeyError, IndexError, AttributeError):
            # This means there is no ASDF extension
            return self

        buff = io.BytesIO(asdf_extension.data)

        try:
            return cls._open_asdf(self, buff, uri=uri, mode='r',
                              validate_checksums=validate_checksums,
                              strict_extension_check=strict_extension_check,
                              ignore_missing_extensions=ignore_missing_extensions,
                              validate_on_read=validate_on_read)
        except RuntimeError:
            self.close()
            raise

    def _create_hdu(self, buff, use_image_hdu):
        # Allow writing to old-style ImageHDU for backwards compatibility
        if use_image_hdu:
            array = np.frombuffer(buff.getvalue(), np.uint8)
            return fits.ImageHDU(array, name=ASDF_EXTENSION_NAME)
        else:
            data = np.array(buff.getbuffer(), dtype=np.uint8)[None, :]
            fmt = '{}B'.format(len(data[0]))
            column = fits.Column(array=data, format=fmt, name='ASDF_METADATA')
            return fits.BinTableHDU.from_columns([column], name=ASDF_EXTENSION_NAME)

    def _update_asdf_extension(self, all_array_storage=None,
                               all_array_compression=None, auto_inline=None,
                               pad_blocks=False, use_image_hdu=False):
        if self.blocks.streamed_block is not None:
            raise ValueError(
                "Can not save streamed data to ASDF-in-FITS file.")

        buff = io.BytesIO()
        super(AsdfInFits, self).write_to(
            buff, all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            auto_inline=auto_inline, pad_blocks=pad_blocks,
            include_block_index=False)

        if ASDF_EXTENSION_NAME in self._hdulist:
            del self._hdulist[ASDF_EXTENSION_NAME]
        self._hdulist.append(self._create_hdu(buff, use_image_hdu))

    def write_to(self, filename, all_array_storage=None,
                 all_array_compression=None, auto_inline=None,
                 pad_blocks=False, use_image_hdu=False, *args, **kwargs):
        self._update_asdf_extension(
            all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            auto_inline=auto_inline, pad_blocks=pad_blocks,
            use_image_hdu=use_image_hdu)

        self._hdulist.writeto(filename, *args, **kwargs)

    def update(self, all_array_storage=None, all_array_compression=None,
               auto_inline=None, pad_blocks=False):
        raise NotImplementedError(
            "In-place update is not currently implemented for ASDF-in-FITS")

        self._update_asdf_extension(
            all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            auto_inline=auto_inline, pad_blocks=pad_blocks)
