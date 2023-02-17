import sys

import pytest

from asdf.exceptions import AsdfDeprecationWarning
from asdf.types import CustomType


def test_custom_type_warning():
    with pytest.warns(AsdfDeprecationWarning, match=r"^.* subclasses the deprecated CustomType .*$"):

        class NewCustomType(CustomType):
            pass


def test_asdf_in_fits_import_warning():
    if "asdf.fits_embed" in sys.modules:
        del sys.modules["asdf.fits_embed"]
    with pytest.warns(AsdfDeprecationWarning, match="AsdfInFits has been deprecated.*"):
        import asdf.fits_embed  # noqa: F401
