# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import importlib

from .exploded import *
from .to_yaml import *
from .defragment import *
from .diff import *
from .tags import *
from .extension import *

# Extracting ASDF-in-FITS files requires Astropy
if importlib.util.find_spec('astropy'):
    from .extract import *
    from .remove_hdu import *
