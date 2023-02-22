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
from ._types import CustomType
from ._version import version as __version__
from .asdf import AsdfFile
from .asdf import open_asdf as open  # noqa: A001
from .config import config_context, get_config
from .stream import Stream
from .tags.core import IntegerType
from .tags.core.external_reference import ExternalArrayReference


def __getattr__(name):
    if name == "AsdfExtension":
        # defer import to only issue deprecation warning when
        # asdf.AsdfExtension is used
        from asdf import extension

        return extension.AsdfExtension
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
