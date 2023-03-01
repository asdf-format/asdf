"""
This module is deprecated. Please see :ref:`extending_converters`
"""
import warnings

from . import _types
from .exceptions import AsdfDeprecationWarning


def _warn():
    warnings.warn(
        "asdf.types is deprecated "
        "Please see the new extension API "
        "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
        AsdfDeprecationWarning,
    )


_warn()
__all__ = _types.__all__  # noqa: PLE0605


def __getattr__(name):
    attr = getattr(_types, name)
    _warn()
    if hasattr(attr, "__module__") and name != "format_tag":
        attr.__module__ = __name__
    return attr
