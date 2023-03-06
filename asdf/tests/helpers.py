"""
This module is deprecated. Please see `asdf.testing.helpers`
"""
import warnings

from asdf._tests import _helpers
from asdf.exceptions import AsdfDeprecationWarning


def _warn():
    warnings.warn(
        "asdf.tests.helpers is deprecated. Please see asdf.testing.helpers",
        AsdfDeprecationWarning,
    )


_warn()

__all__ = _helpers.__all__  # noqa: PLE0605


def __getattr__(name):
    _warn()
    attr = getattr(_helpers, name)
    if hasattr(attr, "__module__"):
        attr.__module__ = __name__  # make automodapi think this is local
    return attr
