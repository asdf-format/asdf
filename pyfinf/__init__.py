# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

"""
PyFINF: Python library for reading and writing FINF files
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *
# ----------------------------------------------------------------------------

__all__ = ['FinfFile', 'open', 'test']

from .finf import FinfFile
from .stream import Stream


def open(init, mode='rw', uri=None):
    """
    Open a FinfFile.

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
    return FinfFile.read(init, mode=mode, uri=uri)
