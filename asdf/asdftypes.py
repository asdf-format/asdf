# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import warnings

from .exceptions import AsdfDeprecationWarning
# This is not exhaustive, but represents the public API
from .versioning import join_tag_version, split_tag_version
from .types import (AsdfType, CustomType, format_tag, ExtensionTypeMeta,
                    _all_asdftypes)

__all__ = ['join_tag_version', 'split_tag_version', 'AsdfType', 'CustomType',
    'format_tag', 'ExtensionTypeMeta', '_all_asdftypes']

warnings.warn(
    "The module asdf.asdftypes has been deprecated and will be removed in 3.0. "
    "Use asdf.types instead.", AsdfDeprecationWarning)
