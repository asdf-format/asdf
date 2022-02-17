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
    "info",
    "__version__",
    "ValidationError",
    "get_config",
    "config_context",
]

from jsonschema import ValidationError

from ._convenience import info
from .asdf import AsdfFile
from .asdf import open_asdf as open
from .config import config_context, get_config
from .extension import AsdfExtension
from .stream import Stream
from .types import CustomType
from .version import version as __version__
