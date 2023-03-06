"""
This module is deprecated. Please see :ref:`extending_converters`
"""
import warnings

from . import _type_index
from .exceptions import AsdfDeprecationWarning


def _warn():
    warnings.warn(
        "asdf.type_index is deprecated "
        "Please see the new extension API "
        "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
        AsdfDeprecationWarning,
    )


_warn()
__all__ = _type_index.__all__  # noqa: PLE0605


def __getattr__(name):
    attr = getattr(_type_index, name)
    _warn()
    if hasattr(attr, "__module__"):
        attr.__module__ = __name__
    return attr
