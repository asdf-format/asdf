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
# overwrite the module name for each defined class to allow doc references to work
for class_ in [
    _types.ExtensionTypeMeta,
    _types.AsdfTypeMeta,
    _types.ExtensionType,
    _types.AsdfType,
    _types.CustomType,
]:
    class_.__module__ = __name__
sys.modules[__name__] = _types
