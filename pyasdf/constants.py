# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


ASDF_MAGIC = b'%ASDF '
BLOCK_MAGIC = b'\xd3BLK'


YAML_TAG_PREFIX = 'tag:yaml.org,2002:'
YAML_END_MARKER_REGEX = br'\r?\n\.\.\.\r?\n'


STSCI_SCHEMA_URI_BASE = 'http://stsci.edu/schemas/'


BLOCK_FLAG_STREAMED = 0x1
