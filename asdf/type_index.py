import sys
import warnings

from . import _type_index
from .exceptions import AsdfDeprecationWarning

warnings.warn(
    "asdf.type_index is deprecated "
    "Please see the new extension API "
    "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
    AsdfDeprecationWarning,
)


# overwrite the hidden module __file__ so pytest doesn't throw an ImportPathMismatchError
_type_index.__file__ = __file__
# overwrite the module name for each defined class to allow doc references to work
for class_ in [
    _type_index._AsdfWriteTypeIndex,
    _type_index.AsdfTypeIndex,
]:
    class_.__module__ = __name__
sys.modules[__name__] = _type_index
