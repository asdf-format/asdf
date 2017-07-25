# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

"""
asdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._internal_init import *
# ----------------------------------------------------------------------------

if _ASDF_SETUP_ is False:
    __all__ = ['AsdfFile', 'CustomType', 'AsdfExtension',
               'Stream', 'open', 'test', 'commands',
               'ValidationError']

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

    from jsonschema import ValidationError

    class ValidationError(ValidationError):
        pass

    open = AsdfFile.open
