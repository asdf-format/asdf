"""
asdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

__all__ = [
    "AsdfFile",
    "CustomType",
    "AsdfExtension",
    "Stream",
    "open",
    "IntegerType",
    "ExternalArrayReference",
    "info",
    "__version__",
    "ValidationError",
    "get_config",
    "config_context",
]


from jsonschema import ValidationError

from ._convenience import info
from ._version import version as __version__
from .asdf import AsdfFile
from .asdf import open_asdf as open
from .config import config_context, get_config
from .extension import AsdfExtension
from .stream import Stream
from .tags.core import IntegerType
from .tags.core.external_reference import ExternalArrayReference
from .types import CustomType
