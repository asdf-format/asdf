# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


"""
asdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._internal_init import *
# ----------------------------------------------------------------------------

__all__ = [
    'AsdfFile', 'CustomType', 'AsdfExtension', 'Stream', 'open', 'test',
    'commands', 'ExternalArrayReference'
]

try:
    import yaml as _
except ImportError:
    raise ImportError("asdf requires pyyaml")

try:
    import jsonschema as _
except ImportError:
    raise ImportError("asdf requires jsonschema")

try:
    import numpy as _
except ImportError:
    raise ImportError("asdf requires numpy")

from .asdf import AsdfFile
from .asdftypes import CustomType
from .extension import AsdfExtension
from .stream import Stream
from . import commands
from .tags.core.external_reference import ExternalArrayReference

from jsonschema import ValidationError

# TODO: there doesn't seem to be any reason to redefine this here
class ValidationError(ValidationError):
    pass

try:
    from astropy.io import fits
except ImportError:
    pass
else:
    from .fits_embed import _AsdfHDU
    fits.register_hdu(_AsdfHDU)

open = AsdfFile.open
