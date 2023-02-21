"""
Implementation of command for removing ASDF HDU from ASDF-in-FITS file.
"""

import warnings

from astropy.io import fits

from asdf.exceptions import AsdfWarning

from .main import Command

__all__ = ["remove_hdu"]


class FitsExtractor(Command):  # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""

    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "remove-hdu",
            help="Remove ASDF extension from ASDF-in-FITS file",
            description="Removes ASDF extensions from ASDF-in-FITS files.",
        )

        parser.add_argument(
            "infile",
            action="store",
            type=str,
            help="Name of ASDF-in-FITS file containing extension to be removed",
        )
        parser.add_argument("outfile", action="store", type=str, help="Name of new FITS output file")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return remove_hdu(args.infile, args.outfile)


def remove_hdu(input_file, output_file):
    """Function for removing ASDF HDU from ASDF-in-FITS files"""
    # issue a non-deprecation warning here so that any usage of this command
    # displays a warning
    warnings.warn(
        "remove-hdu is deprecated and will be removed in asdf-3.0. "
        "Support for AsdfInFits files has been added to stdatamodels "
        "https://github.com/spacetelescope/stdatamodels",
        AsdfWarning,
    )
    # local import to trigger the deprecation warning since this command
    # relates to and mentions AsdfInFits
    from asdf.fits_embed import AsdfInFits  # noqa: F401

    try:
        with fits.open(input_file) as hdulist:
            hdulist.readall()
            asdf_hdu = hdulist["ASDF"]
            hdulist.remove(asdf_hdu)
            hdulist.writeto(output_file)
    except (ValueError, KeyError) as err:
        raise RuntimeError(str(err)) from err
