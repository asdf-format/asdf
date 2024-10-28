import pytest

import asdf
import asdf.testing.helpers
from asdf.exceptions import AsdfDeprecationWarning, ValidationError


def test_find_references_during_init_deprecation():
    tree = {"a": 1, "b": {"$ref": "#"}}
    with pytest.warns(AsdfDeprecationWarning, match="find_references during AsdfFile.__init__"):
        asdf.AsdfFile(tree)
