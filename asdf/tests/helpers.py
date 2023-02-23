"""
This module is deprecated. Please see `asdf.testing.helpers`
"""
import warnings

from asdf.exceptions import AsdfDeprecationWarning

from . import _helpers

warnings.warn(
    "asdf.tests.helpers is deprecated. Please see asdf.testing.helpers",
    AsdfDeprecationWarning,
)


__all__ = _helpers.__all__  # noqa: PLE0605


def __getattr__(name):
    warnings.warn(
        "asdf.tests.helpers is deprecated. Please see asdf.testing.helpers",
        AsdfDeprecationWarning,
    )
    attr = getattr(_helpers, name)
    attr.__module__ = __name__  # make automodapi think this is local
    return attr
