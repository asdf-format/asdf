from packaging.specifiers import SpecifierSet

from asdf.extension import BuiltinExtension, ExtensionProxy, AsdfExtension

from asdf.tests.helpers import assert_extension_correctness


def test_builtin_extension():
    extension = BuiltinExtension()
    assert_extension_correctness(extension)


def test_asdf_extension():
    class EmptyExtension:
        pass

    # Currently the AsdfExtension does not have required attributes:
    assert issubclass(EmptyExtension, AsdfExtension)


def test_proxy_maybe_wrap():
    class TestExtension:
        extension_uri = "http://somewhere.org/extensions/test"

    extension = TestExtension()
    proxy = ExtensionProxy.maybe_wrap(extension)
    assert proxy.delegate is extension
    assert ExtensionProxy.maybe_wrap(proxy) is proxy


def test_proxy_properties():
    class TestExtension:
        extension_uri = "http://somewhere.org/extensions/test"
        default = True
        always_enabled = True
        legacy_class_names = {
            "org.foo.extensions.SomeLegacyClass",
            "org.foo.extensions.SomeOtherLegacyClass",
        }
        asdf_standard_requirement = ">=1.5, <2"
    proxy = ExtensionProxy(TestExtension(), package_name="foo", package_version="1.2.3")

    assert proxy.extension_uri == "http://somewhere.org/extensions/test"
    assert proxy.default is True
    assert proxy.always_enabled is True
    assert proxy.legacy_class_names == {
        "org.foo.extensions.SomeLegacyClass",
        "org.foo.extensions.SomeOtherLegacyClass"
    }
    assert proxy.asdf_standard_requirement == SpecifierSet(">=1.5, <2")
    assert proxy.legacy is False
    assert proxy.package_name == "foo"
    assert proxy.package_version == "1.2.3"
    assert proxy.class_name.endswith(".TestExtension")


def test_proxy_repr():
    class TestExtension:
        extension_uri = "http://somewhere.org/extensions/test"
        default = True
        always_enabled = True
        legacy_class_names = {
            "org.foo.extensions.SomeLegacyClass",
            "org.foo.extensions.SomeOtherLegacyClass",
        }
        asdf_standard_requirement = ">=1.5, <2"
    proxy = ExtensionProxy(TestExtension(), package_name="foo", package_version="1.2.3")

    assert "URI: http://somewhere.org/extensions/test" in repr(proxy)
    assert ".TestExtension" in repr(proxy)
    assert "package: foo==1.2.3" in repr(proxy)
    assert "ASDF Standard: " + str(proxy.asdf_standard_requirement) in repr(proxy)

    class EmptyExtension:
        pass
    empty_proxy = ExtensionProxy(EmptyExtension(), legacy=True)

    assert "URI: (none)" in repr(empty_proxy)
    assert ".EmptyExtension" in repr(empty_proxy)
    assert "package: (none)" in repr(empty_proxy)
    assert "ASDF Standard: (all)" in repr(empty_proxy)


def test_extension_defaults():
    """
    This test compares defaults from ExtensionProxy
    to defaults defined in AsdfExtension, which should
    be identical.
    """
    class TestAsdfExtension(AsdfExtension):
        pass
    asdf_extension = TestAsdfExtension()

    class TestExtension:
        pass
    proxy = ExtensionProxy(TestExtension(), legacy=True)

    assert proxy.extension_uri is None
    assert proxy.extension_uri == asdf_extension.extension_uri

    assert proxy.default is False
    assert asdf_extension.default == proxy.default

    assert proxy.always_enabled is False
    assert asdf_extension.always_enabled == proxy.always_enabled

    assert proxy.legacy_class_names == set()
    assert asdf_extension.legacy_class_names == proxy.legacy_class_names

    assert proxy.asdf_standard_requirement == SpecifierSet()
    assert asdf_extension.asdf_standard_requirement is None

    assert proxy.types == []
    assert asdf_extension.types == proxy.types

    assert proxy.tag_mapping == []
    assert asdf_extension.tag_mapping == proxy.tag_mapping

    assert proxy.url_mapping == []
    assert asdf_extension.url_mapping == proxy.url_mapping

    assert proxy.legacy is True
