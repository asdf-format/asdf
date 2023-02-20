import sys
import warnings

from . import _types
from .exceptions import AsdfDeprecationWarning

warnings.warn(
    "asdf.types is deprecated "
    "Please see the new extension API "
    "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
    AsdfDeprecationWarning,
)


# overwrite the hidden module __file__ so pytest doesn't throw an ImportPathMismatchError
_types.__file__ = __file__
sys.modules[__name__] = _types
