# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import numpy as np


ASDF_MAGIC = b'#ASDF'
BLOCK_MAGIC = b'\xd3BLK'
BLOCK_HEADER_BOILERPLATE_SIZE = 6

ASDF_STANDARD_COMMENT = b'ASDF_STANDARD'

INDEX_HEADER = b'#ASDF BLOCK INDEX'

# The maximum number of blocks supported
MAX_BLOCKS = 2 ** 16
MAX_BLOCKS_DIGITS = int(np.ceil(np.log10(MAX_BLOCKS) + 1))

YAML_TAG_PREFIX = 'tag:yaml.org,2002:'
YAML_END_MARKER_REGEX = br'\r?\n\.\.\.((\r?\n)|$)'


STSCI_SCHEMA_URI_BASE = 'http://stsci.edu/schemas/'
STSCI_SCHEMA_TAG_BASE = 'tag:stsci.edu:asdf'


BLOCK_FLAG_STREAMED = 0x1
