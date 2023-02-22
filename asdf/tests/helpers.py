import sys
import warnings

from asdf.exceptions import AsdfDeprecationWarning

from . import _helpers

warnings.warn(
    "asdf.tests.helpers is deprecated. Please see asdf.testing.helpers",
    AsdfDeprecationWarning,
)

# overwrite the hidden module __file__ so pytest doesn't throw an ImportPathMismatchError
_helpers.__file__ = __file__
sys.modules[__name__] = _helpers
