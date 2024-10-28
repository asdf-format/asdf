import sys
import warnings

import pytest

import asdf
import asdf.testing.helpers
from asdf.exceptions import AsdfDeprecationWarning, ValidationError


def test_asdf_stream_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.stream is deprecated"):
        if "asdf.stream" in sys.modules:
            del sys.modules["asdf.stream"]
        import asdf.stream  # noqa: F401


def test_asdf_asdf_SerializationContext_import_deprecation():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=AsdfDeprecationWarning,
            message="asdf.asdf is deprecated. Please use asdf.AsdfFile and asdf.open",
        )
        warnings.filterwarnings(
            "ignore",
            category=AsdfDeprecationWarning,
            message="asdf.asdf is deprecated",
        )
        with pytest.warns(AsdfDeprecationWarning, match="importing SerializationContext from asdf.asdf"):
            from asdf.asdf import SerializationContext  # noqa: F401


def test_asdf_util_human_list_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.human_list is deprecated"):
        asdf.util.human_list("a")


def test_asdf_util_resolve_name_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.resolve_name is deprecated"):
        asdf.util.resolve_name("asdf.AsdfFile")


def test_asdf_asdf_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.asdf is deprecated"):
        if "asdf.asdf" in sys.modules:
            del sys.modules["asdf.asdf"]
        import asdf.asdf  # noqa: F401


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


@pytest.mark.parametrize("value", [True, False])
def test_AsdfFile_ignore_implicit_conversion_deprecation(value):
    with pytest.warns(AsdfDeprecationWarning, match="ignore_implicit_conversion is deprecated"):
        asdf.AsdfFile({"a": 1}, ignore_implicit_conversion=value)


@pytest.mark.parametrize("value", [True, False])
def test_walk_and_modify_ignore_implicit_conversion_deprecation(value):
    with pytest.warns(AsdfDeprecationWarning, match="ignore_implicit_conversion is deprecated"):
        asdf.treeutil.walk_and_modify({}, lambda obj: obj, ignore_implicit_conversion=value)


@pytest.mark.parametrize("value", [True, False])
def test_ignore_version_mismatch_deprecation(value):
    with pytest.warns(AsdfDeprecationWarning, match="ignore_version_mismatch is deprecated"):
        asdf.AsdfFile({}, ignore_version_mismatch=value)
