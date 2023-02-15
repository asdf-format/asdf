import pytest

from asdf.exceptions import AsdfDeprecationWarning
from asdf.types import CustomType


def test_custom_type_warning():
    with pytest.warns(AsdfDeprecationWarning, match=r"^.* subclasses the deprecated CustomType .*$"):

        class NewCustomType(CustomType):
            pass
