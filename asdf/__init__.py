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


from ._convenience import info
from ._version import version as __version__
from .asdf import AsdfFile
from .asdf import open_asdf as open
from .config import config_context, get_config
from .exceptions import ValidationError
from .tags.core import IntegerType, Stream
from .tags.core.external_reference import ExternalArrayReference


def __getattr__(name):
    if name == "stream":
        import warnings

        import asdf.tags.core.stream
        from asdf.exceptions import AsdfDeprecationWarning

        warnings.warn(
            "asdf.stream is deprecated. Please use asdf.tags.core.stream",
            AsdfDeprecationWarning,
        )

        return asdf.tags.core.stream

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
