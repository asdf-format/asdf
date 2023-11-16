"""
asdf: Python library for reading and writing Advanced Scientific
Data Format (ASDF) files
"""

__all__ = [
    "AsdfFile",
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


from ._asdf import AsdfFile
from ._asdf import open_asdf as open
from ._convenience import info
from ._version import version as __version__
from .config import config_context, get_config
from .exceptions import ValidationError
from .tags.core import IntegerType, Stream
from .tags.core.external_reference import ExternalArrayReference
