import pytest

import asdf
import asdf.testing.helpers
from asdf.exceptions import AsdfDeprecationWarning, ValidationError


def test_find_references_during_init_deprecation():
    tree = {"a": 1, "b": {"$ref": "#"}}
    with pytest.warns(AsdfDeprecationWarning, match="find_references during AsdfFile.__init__"):
        asdf.AsdfFile(tree)


def test_find_references_during_open_deprecation(tmp_path):
    fn = tmp_path / "test.asdf"
    af = asdf.AsdfFile()
    af["a"] = 1
    af["b"] = {"$ref": "#"}
    af.write_to(fn)
    with pytest.warns(AsdfDeprecationWarning, match="find_references during open"):
        with asdf.open(fn) as af:
            pass
