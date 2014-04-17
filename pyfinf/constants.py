# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


FINF_MAGIC = b'%FINF '
BLOCK_MAGIC = b'\xd3BFF\r\n \n'


YAML_TAG_PREFIX = 'tag:yaml.org,2002:'
YAML_END_MARKER_REGEX = br'\r?\n\.\.\.\r?\n'


STSCI_SCHEMA_URI_BASE = 'http://www.stsci.edu/schemas/'
