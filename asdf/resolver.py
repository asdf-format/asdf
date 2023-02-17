import sys
import warnings

from . import _resolver
from .exceptions import AsdfDeprecationWarning

warnings.warn(
    "asdf.resolver is deprecated "
    "Please see Resources "
    "https://asdf.readthedocs.io/en/stable/asdf/extending/resources.html",
    AsdfDeprecationWarning,
)

# overwrite the hidden module __file__ so pytest doesn't throw an ImportPathMismatchError
_resolver.__file__ = __file__
sys.modules[__name__] = _resolver
