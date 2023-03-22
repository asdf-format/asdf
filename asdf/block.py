"""
This module is deprecated. Direct use of the block manager was never intended
"""
import warnings

from . import _block
from .exceptions import AsdfDeprecationWarning


def _warn():
    warnings.warn(
        "asdf.block is deprecated direct use of the block manager was never intended",
        AsdfDeprecationWarning,
    )


_warn()


def __getattr__(name):
    attr = getattr(_block, name)
    _warn()
    if hasattr(attr, "__module__"):
        attr.__module__ = __name__
    return attr


def __dir__():
    return dir(_block)
