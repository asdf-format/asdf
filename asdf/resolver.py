"""
This module is deprecated. Please see :ref:`extending_resources`
"""
import warnings

from . import _resolver
from .exceptions import AsdfDeprecationWarning


def _warn():
    warnings.warn(
        "asdf.resolver is deprecated "
        "Please see Resources "
        "https://asdf.readthedocs.io/en/stable/asdf/extending/resources.html",
        AsdfDeprecationWarning,
    )


_warn()


def __getattr__(name):
    attr = getattr(_resolver, name)
    _warn()
    if hasattr(attr, "__module__"):
        attr.__module__ = __name__
    return attr


def __dir__():
    return dir(_resolver)
