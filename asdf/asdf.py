import warnings

from . import _asdf
from .exceptions import AsdfDeprecationWarning

warnings.warn(
    "asdf.asdf is deprecated. Please use asdf.AsdfFile and asdf.open",
    AsdfDeprecationWarning,
)


def __getattr__(name):
    if hasattr(_asdf, name):
        return getattr(_asdf, name)
    warnings.warn(
        "asdf.asdf is deprecated",
        AsdfDeprecationWarning,
    )
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
