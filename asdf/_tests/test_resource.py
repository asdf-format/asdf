from collections.abc import Mapping

import pytest

from asdf.resource import JsonschemaResourceMapping, ResourceManager, ResourceMappingProxy


def test_resource_manager():
    mapping1 = {
        "http://somewhere.org/schemas/foo-1.0.0": b"foo",
        "http://somewhere.org/schemas/bar-1.0.0": b"bar",
    }
    mapping2 = {
        "http://somewhere.org/schemas/foo-1.0.0": b"duplicate foo",
        "http://somewhere.org/schemas/baz-1.0.0": b"baz",
        "http://somewhere.org/schemas/foz-1.0.0": "foz",
    }
    manager = ResourceManager([mapping1, mapping2])

    assert isinstance(manager, Mapping)

    assert len(manager) == 4
    assert set(manager) == {
        "http://somewhere.org/schemas/foo-1.0.0",
        "http://somewhere.org/schemas/bar-1.0.0",
        "http://somewhere.org/schemas/baz-1.0.0",
        "http://somewhere.org/schemas/foz-1.0.0",
    }
    assert "http://somewhere.org/schemas/foo-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/foo-1.0.0"] == b"foo"
    assert "http://somewhere.org/schemas/bar-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/bar-1.0.0"] == b"bar"
    assert "http://somewhere.org/schemas/baz-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/baz-1.0.0"] == b"baz"
    assert "http://somewhere.org/schemas/foz-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/foz-1.0.0"] == b"foz"

    with pytest.raises(KeyError, match=r"http://somewhere.org/schemas/missing-1.0.0"):
        manager["http://somewhere.org/schemas/missing-1.0.0"]

    # Confirm that the repr string is reasonable:
    assert "len: 4" in repr(manager)


def test_jsonschema_resource_mapping():
    mapping = JsonschemaResourceMapping()
    assert isinstance(mapping, Mapping)

    assert len(mapping) == 1
    assert set(mapping) == {"http://json-schema.org/draft-04/schema"}
    assert "http://json-schema.org/draft-04/schema" in mapping
    assert b"http://json-schema.org/draft-04/schema" in mapping["http://json-schema.org/draft-04/schema"]

    assert repr(mapping) == "JsonschemaResourceMapping()"


def test_proxy_is_mapping():
    assert isinstance(ResourceMappingProxy({}), Mapping)


def test_proxy_maybe_wrap():
    mapping = {
        "http://somewhere.org/resources/foo": "foo",
        "http://somewhere.org/resources/bar": "bar",
    }

    proxy = ResourceMappingProxy.maybe_wrap(mapping)
    assert proxy.delegate is mapping
    assert ResourceMappingProxy.maybe_wrap(proxy) is proxy

    with pytest.raises(TypeError, match=r"Resource mapping must implement the Mapping interface"):
        ResourceMappingProxy.maybe_wrap([])


def test_proxy_properties():
    mapping = {
        "http://somewhere.org/resources/foo": "foo",
        "http://somewhere.org/resources/bar": "bar",
    }

    proxy = ResourceMappingProxy(mapping, package_name="foo", package_version="1.2.3")

    assert len(proxy) == len(mapping)
    assert set(proxy.keys()) == set(mapping.keys())
    for uri in mapping:
        assert proxy[uri] is mapping[uri]

    assert proxy.package_name == "foo"
    assert proxy.package_version == "1.2.3"
    assert proxy.class_name.endswith("dict")


def test_proxy_hash_and_eq():
    mapping = {
        "http://somewhere.org/resources/foo": "foo",
        "http://somewhere.org/resources/bar": "bar",
    }
    proxy1 = ResourceMappingProxy(mapping)
    proxy2 = ResourceMappingProxy(mapping, package_name="foo", package_version="1.2.3")

    assert proxy1 == proxy2
    assert hash(proxy1) == hash(proxy2)
    assert proxy1 != mapping
    assert proxy2 != mapping


def test_proxy_repr():
    mapping = {
        "http://somewhere.org/resources/foo": "foo",
        "http://somewhere.org/resources/bar": "bar",
    }

    proxy = ResourceMappingProxy(mapping, package_name="foo", package_version="1.2.3")

    assert ".dict" in repr(proxy)
    assert "package: foo==1.2.3" in repr(proxy)
    assert "len: 2" in repr(proxy)

    empty_proxy = ResourceMappingProxy({})

    assert ".dict" in repr(empty_proxy)
    assert "package: (none)" in repr(empty_proxy)
    assert "len: 0" in repr(empty_proxy)
