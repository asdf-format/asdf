import sys

import numpy as np
import pytest

import asdf
from asdf.exceptions import AsdfDeprecationWarning


def test_asdf_stream_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.stream is deprecated"):
        if "asdf.stream" in sys.modules:
            del sys.modules["asdf.stream"]
        import asdf.stream  # noqa: F401


def test_asdf_asdf_SerializationContext_import_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="importing SerializationContext from asdf.asdf"):
        from asdf.asdf import SerializationContext  # noqa: F401


def test_asdf_util_human_list_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.human_list is deprecated"):
        asdf.util.human_list("a")


def test_asdf_util_resolve_name_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.resolve_name is deprecated"):
        asdf.util.resolve_name("asdf.AsdfFile")


def test_asdf_util_minversion_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.minversion is deprecated"):
        asdf.util.minversion("yaml", "3.1")


def test_asdf_util_iter_subclasses_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.iter_subclasses is deprecated"):
        list(asdf.util.iter_subclasses(asdf.AsdfFile))


def test_asdf_asdf_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.asdf is deprecated"):
        if "asdf.asdf" in sys.modules:
            del sys.modules["asdf.asdf"]
        import asdf.asdf  # noqa: F401


def test_resolve_and_inline_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="resolve_and_inline is deprecated"):
        af = asdf.AsdfFile({"arr": np.arange(42)})
        af.resolve_and_inline()


@pytest.mark.parametrize("force_raw_types", [True, False])
def test_tagged_tree_to_custom_tree_force_raw_types_deprecation(tmp_path, force_raw_types):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"a": np.zeros(3)}).write_to(fn)

    with asdf.open(fn, tree_type="tagged") as af:
        with pytest.warns(AsdfDeprecationWarning, match="force_raw_types is deprecated"):
            asdf.yamlutil.tagged_tree_to_custom_tree(af.tree, af, force_raw_types)


@pytest.mark.parametrize("force_raw_types", [True, False])
def test_asdf_open_force_raw_types_deprecation(tmp_path, force_raw_types):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"a": np.zeros(3)}).write_to(fn)

    with pytest.warns(AsdfDeprecationWarning, match="_force_raw_types is deprecated"):
        with asdf.open(fn, _force_raw_types=force_raw_types) as af:
            if force_raw_types:
                assert isinstance(af["a"], asdf.tagged.TaggedDict)
            else:
                assert isinstance(af["a"], asdf.tags.core.ndarray.NDArrayType)
