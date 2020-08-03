import pytest

from asdf.extension import BuiltinExtension, ExtensionProxy
from asdf.types import CustomType

from asdf.tests.helpers import assert_extension_correctness

def test_builtin_extension():
    extension = BuiltinExtension()
    assert_extension_correctness(extension)


class LegacyType(dict, CustomType):
    organization = "somewhere.org"
    name = "test"
    version = "1.0.0"


class LegacyExtension:
    types = [LegacyType]
    tag_mapping = [("tag:somewhere.org/", "http://somewhere.org/{tag_suffix}")]
    url_mapping = [("http://somewhere.org/", "http://somewhere.org/{url_suffix}.yaml")]


def test_proxy_maybe_wrap():
    extension = LegacyExtension()
    proxy = ExtensionProxy.maybe_wrap(extension)
    assert proxy.delegate is extension
    assert ExtensionProxy.maybe_wrap(proxy) is proxy

    with pytest.raises(TypeError):
        ExtensionProxy.maybe_wrap(object())


def test_proxy_legacy():
    extension = LegacyExtension()
    proxy = ExtensionProxy(extension, package_name="foo", package_version="1.2.3")

    assert proxy.types == [LegacyType]
    assert proxy.tag_mapping == LegacyExtension.tag_mapping
    assert proxy.url_mapping == LegacyExtension.url_mapping
    assert proxy.delegate is extension
    assert proxy.legacy is True
    assert proxy.package_name == "foo"
    assert proxy.package_version == "1.2.3"
    assert proxy.class_name == "asdf.tests.test_extension.LegacyExtension"


def test_proxy_hash_and_eq():
    extension = LegacyExtension()
    proxy1 = ExtensionProxy(extension)
    proxy2 = ExtensionProxy(extension, package_name="foo", package_version="1.2.3")

    assert proxy1 == proxy2
    assert hash(proxy1) == hash(proxy2)
    assert proxy1 != extension
    assert proxy2 != extension


def test_proxy_repr():
    proxy = ExtensionProxy(LegacyExtension(), package_name="foo", package_version="1.2.3")
    assert "class: asdf.tests.test_extension.LegacyExtension" in repr(proxy)
    assert "package: foo==1.2.3" in repr(proxy)
    assert "legacy: True" in repr(proxy)

    proxy = ExtensionProxy(LegacyExtension())
    assert "class: asdf.tests.test_extension.LegacyExtension" in repr(proxy)
    assert "package: (none)" in repr(proxy)
    assert "legacy: True" in repr(proxy)
