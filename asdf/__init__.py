# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
asdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

from pkg_resources import get_distribution, DistributionNotFound

try:
    version = get_distribution('asdf').version
    __version__ = version
except DistributionNotFound:
    # package is not installed
    version = "unknown"
    __version__ = version

from jsonschema import ValidationError

from .asdf import AsdfFile, open_asdf
from .types import CustomType
from .extension import AsdfExtension
from .stream import Stream
from . import commands
from .tags.core import IntegerType
from .tags.core.external_reference import ExternalArrayReference



__all__ = [
    'AsdfFile', 'CustomType', 'AsdfExtension', 'Stream', 'open', 'version',
    'commands', 'IntegerType', 'ExternalArrayReference', 'ValidationError',
]

open = open_asdf
# Avoid redundancy/confusion in the top-level namespace
del open_asdf

def test(*args, **kwargs):
    raise DeprecationWarning("asdf.test() is no longer supported. "
        "Use pytest instead.")
