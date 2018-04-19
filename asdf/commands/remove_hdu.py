# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Implementation of command for removing ASDF HDU from ASDF-in-FITS file.
"""

import sys

from astropy.io import fits

from .main import Command


__all__ = ['remove_hdu']


class FitsExtractor(Command): # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""

    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(str("remove-hdu"),
            help="Remove ASDF extension from ASDF-in-FITS file",
            description="Removes ASDF extensions from ASDF-in-FITS files.")

        parser.add_argument('infile', action='store', type=str,
            help="Name of ASDF-in-FITS file containing extension to be removed")
        parser.add_argument('outfile', action='store', type=str,
            help="Name of new FITS output file")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return remove_hdu(args.infile, args.outfile)


def remove_hdu(input_file, output_file):
    """Function for removing ASDF HDU from ASDF-in-FITS files"""

    try:
        with fits.open(input_file) as hdulist:
            hdulist.readall()
            asdf_hdu = hdulist['ASDF']
            hdulist.remove(asdf_hdu)
            hdulist.writeto(output_file)
    except (ValueError, KeyError) as error:
        raise RuntimeError(str(error))
