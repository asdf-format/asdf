# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

"""
pyasdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *
# ----------------------------------------------------------------------------

__all__ = ['AsdfFile', 'Stream', 'open', 'test']

from .asdf import AsdfFile
from .stream import Stream


def open(init, mode='rw', uri=None):
    """
    Open a `AsdfFile`.

    Parameters
    ----------
    fd : string or file-like object
        May be a string ``file`` or ``http`` URI, or a Python
        file-like object.

    mode : string, optional
        Must be ``"r"`` (read), ``"w"`` (write) or ``"rw"``
        (read/write).  Default: ``"rw"``.

    uri : string, optional
        The URI of the file.  Only required if the URI can not be
        automatically determined from `init`.
    """
    return AsdfFile.read(init, mode=mode, uri=uri)
