import sys

import pytest

import asdf
import asdf._types
import asdf.extension
import asdf.testing.helpers
from asdf import entry_points
from asdf._tests._helpers import assert_extension_correctness
from asdf._tests.objects import CustomExtension
from asdf._types import CustomType
from asdf.exceptions import AsdfDeprecationWarning

from .test_entry_points import _monkeypatch_entry_points, mock_entry_points  # noqa: F401


def test_custom_type_warning():
    with pytest.warns(AsdfDeprecationWarning, match=r"^.* subclasses the deprecated CustomType .*$"):

        class NewCustomType(CustomType):
            pass


def test_asdf_in_fits_import_warning():
    if "asdf.fits_embed" in sys.modules:
        del sys.modules["asdf.fits_embed"]
    with pytest.warns(AsdfDeprecationWarning, match="AsdfInFits has been deprecated.*"):
        import asdf.fits_embed  # noqa: F401


def test_resolver_module_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="^asdf.resolver is deprecated.*$"):
        # importlib.reload doesn't appear to work here likely because of the
        # sys.module and __file__ changes in asdf.resolver
        if "asdf.resolver" in sys.modules:
            del sys.modules["asdf.resolver"]
        import asdf.resolver
    # resolver does not define an __all__ so we will define one here
    # for testing purposes
    resolver_all = [
        "Resolver",
        "ResolverChain",
        "DEFAULT_URL_MAPPING",
        "DEFAULT_TAG_TO_URL_MAPPING",
        "default_url_mapping",
        "default_tag_to_url_mapping",
        "default_resolver",
    ]
    for attr in dir(asdf.resolver):
        if attr not in resolver_all:
            continue
        with pytest.warns(AsdfDeprecationWarning, match="^asdf.resolver is deprecated.*$"):
            getattr(asdf.resolver, attr)


def test_assert_extension_correctness_deprecation():
    extension = CustomExtension()
    with pytest.warns(AsdfDeprecationWarning, match="assert_extension_correctness is deprecated.*"):
        assert_extension_correctness(extension)


def test_type_index_module_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="^asdf.type_index is deprecated.*$"):
        # importlib.reload doesn't appear to work here likely because of the
        # sys.module and __file__ changes in asdf.type_index
        if "asdf.type_index" in sys.modules:
            del sys.modules["asdf.type_index"]
        import asdf.type_index
    for attr in asdf.type_index.__all__:
        with pytest.warns(AsdfDeprecationWarning, match="^asdf.type_index is deprecated.*$"):
            getattr(asdf.type_index, attr)


@pytest.mark.parametrize("attr", ["url_mapping", "tag_mapping", "resolver", "extension_list", "type_index"])
def test_asdffile_legacy_extension_api_attr_deprecations(attr):
    with asdf.AsdfFile() as af, pytest.warns(AsdfDeprecationWarning, match=f"AsdfFile.{attr} is deprecated"):
        getattr(af, attr)


def test_asdfile_run_hook_deprecation():
    with asdf.AsdfFile() as af, pytest.warns(AsdfDeprecationWarning, match="AsdfFile.run_hook is deprecated"):
        af.run_hook("foo")


def test_asdfile_run_modifying_hook_deprecation():
    with asdf.AsdfFile() as af, pytest.warns(AsdfDeprecationWarning, match="AsdfFile.run_modifying_hook is deprecated"):
        af.run_modifying_hook("foo")


def test_types_module_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="^asdf.types is deprecated.*$"):
        if "asdf.types" in sys.modules:
            del sys.modules["asdf.types"]
        import asdf.types
    for attr in asdf.types.__all__:
        with pytest.warns(AsdfDeprecationWarning, match="^asdf.types is deprecated.*$"):
            getattr(asdf.types, attr)


def test_default_extensions_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="default_extensions is deprecated"):
        asdf.extension.default_extensions


def test_default_resolver():
    with pytest.warns(AsdfDeprecationWarning, match="get_default_resolver is deprecated"):
        asdf.extension.get_default_resolver()


def test_get_cached_asdf_extension_list_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="get_cached_asdf_extension_list is deprecated"):
        asdf.extension.get_cached_asdf_extension_list([])


def test_asdf_type_format_tag():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.types.format_tag is deprecated"):
        asdf._types.format_tag
    asdf.testing.helpers.format_tag


@pytest.mark.parametrize("name", ["AsdfExtension", "AsdfExtensionList", "BuiltinExtension"])
def test_extension_class_deprecation(name):
    with pytest.warns(AsdfDeprecationWarning, match=f"{name} is deprecated"):
        getattr(asdf.extension, name)


def test_top_level_asdf_extension_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="AsdfExtension is deprecated"):
        asdf.AsdfExtension


def test_deprecated_entry_point(mock_entry_points):  # noqa: F811
    mock_entry_points.append(("asdf_extensions", "legacy", "asdf.tests.test_entry_points:LegacyExtension"))
    with pytest.warns(AsdfDeprecationWarning, match=".* uses the deprecated entry point asdf_extensions"):
        entry_points.get_extensions()


def test_asdf_tests_helpers_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.tests.helpers is deprecated"):
        if "asdf.tests.helpers" in sys.modules:
            del sys.modules["asdf.tests.helpers"]
        import asdf.tests.helpers
    from asdf._tests import _helpers

    for attr in _helpers.__all__:
        with pytest.warns(AsdfDeprecationWarning, match="asdf.tests.helpers is deprecated"):
            getattr(asdf.tests.helpers, attr)


def test_blocks_deprecated():
    af = asdf.AsdfFile()
    with pytest.warns(AsdfDeprecationWarning, match="The property AsdfFile.blocks has been deprecated"):
        af.blocks
