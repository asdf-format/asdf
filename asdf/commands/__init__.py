# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import importlib

from .exploded import implode, explode
from .to_yaml import to_yaml
from .defragment import defragment
from .diff import diff
from .tags import list_tags
from .extension import find_extensions
from .info import info


__all__ = ['implode', 'explode', 'to_yaml', 'defragment', 'diff', 'list_tags',
    'find_extensions', 'info']


# Extracting ASDF-in-FITS files requires Astropy
if importlib.util.find_spec('astropy'):
    from .extract import extract_file
    from .remove_hdu import remove_hdu

    __all__ += ['extract_file', 'remove_hdu']
