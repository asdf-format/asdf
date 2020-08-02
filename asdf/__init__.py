"""
asdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._internal_init import __version__, __githash__, test
# ----------------------------------------------------------------------------

__all__ = [
    'AsdfFile', 'CustomType', 'AsdfExtension', 'Stream', 'open', 'test',
    'commands', 'IntegerType', 'ExternalArrayReference', 'info', '__version__',
    '__githash__', 'ValidationError', 'get_config', 'config_context',
]


from .asdf import AsdfFile, open_asdf as open
from .types import CustomType
from .extension import AsdfExtension
from .stream import Stream
from . import commands
from .tags.core import IntegerType
from .tags.core.external_reference import ExternalArrayReference
from ._convenience import info
from .config import get_config, config_context

from jsonschema import ValidationError
