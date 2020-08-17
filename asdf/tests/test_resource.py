import io
import sys
from pathlib import Path
from collections.abc import Mapping

if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

import pytest

from asdf.resource import (
    DirectoryResourceMapping,
    ResourceManager,
    ResourceMappingProxy,
    get_core_resource_mappings,
    JsonschemaResourceMapping,
)


def test_directory_resource_mapping(tmpdir):
    tmpdir.mkdir("schemas")
    (tmpdir/"schemas").mkdir("nested")
    with (tmpdir/"schemas"/"foo-1.2.3.yaml").open("w") as f:
        f.write("id: http://somewhere.org/schemas/foo-1.2.3\n")
    with (tmpdir/"schemas"/"nested"/"bar-4.5.6.yaml").open("w") as f:
        f.write("id: http://somewhere.org/schemas/nested/bar-4.5.6\n")
    with (tmpdir/"schemas"/"baz-7.8.9").open("w") as f:
        f.write("id: http://somewhere.org/schemas/baz-7.8.9\n")

    mapping = DirectoryResourceMapping(str(tmpdir/"schemas"), "http://somewhere.org/schemas")
    assert isinstance(mapping, Mapping)
    assert len(mapping) == 1
    assert set(mapping) == {"http://somewhere.org/schemas/foo-1.2.3"}
    assert "http://somewhere.org/schemas/foo-1.2.3" in mapping
    assert b"http://somewhere.org/schemas/foo-1.2.3" in mapping["http://somewhere.org/schemas/foo-1.2.3"]
    assert "http://somewhere.org/schemas/baz-7.8.9" not in mapping
    assert "http://somewhere.org/schemas/baz-7.8" not in mapping
    assert "http://somewhere.org/schemas/foo-1.2.3.yaml" not in mapping
    assert "http://somewhere.org/schemas/nested/bar-4.5.6" not in mapping

    mapping = DirectoryResourceMapping(str(tmpdir/"schemas"), "http://somewhere.org/schemas", recursive=True)
    assert len(mapping) == 2
    assert set(mapping) == {"http://somewhere.org/schemas/foo-1.2.3", "http://somewhere.org/schemas/nested/bar-4.5.6"}
    assert "http://somewhere.org/schemas/foo-1.2.3" in mapping
    assert b"http://somewhere.org/schemas/foo-1.2.3" in mapping["http://somewhere.org/schemas/foo-1.2.3"]
    assert "http://somewhere.org/schemas/baz-7.8.9" not in mapping
    assert "http://somewhere.org/schemas/baz-7.8" not in mapping
    assert "http://somewhere.org/schemas/nested/bar-4.5.6" in mapping
    assert b"http://somewhere.org/schemas/nested/bar-4.5.6" in mapping["http://somewhere.org/schemas/nested/bar-4.5.6"]

    mapping = DirectoryResourceMapping(
        str(tmpdir/"schemas"),
        "http://somewhere.org/schemas",
        recursive=True,
        filename_pattern="baz-*",
        stem_filename=False
    )

    assert len(mapping) == 1
    assert set(mapping) == {"http://somewhere.org/schemas/baz-7.8.9"}
    assert "http://somewhere.org/schemas/foo-1.2.3" not in mapping
    assert "http://somewhere.org/schemas/baz-7.8.9" in mapping
    assert b"http://somewhere.org/schemas/baz-7.8.9" in mapping["http://somewhere.org/schemas/baz-7.8.9"]
    assert "http://somewhere.org/schemas/nested/bar-4.5.6" not in mapping

    # Check that the repr is reasonable
    # Need to be careful checking the path string because
    # pathlib normalizes Windows paths.
    assert repr(Path(str(tmpdir/"schemas"))) in repr(mapping)
    assert "http://somewhere.org/schemas" in repr(mapping)
    assert "recursive=True" in repr(mapping)
    assert "filename_pattern='baz-*'" in repr(mapping)
    assert "stem_filename=False" in repr(mapping)

    # Make sure trailing slash is handled correctly
    mapping = DirectoryResourceMapping(str(tmpdir/"schemas"), "http://somewhere.org/schemas/")
    assert len(mapping) == 1
    assert set(mapping) == {"http://somewhere.org/schemas/foo-1.2.3"}
    assert "http://somewhere.org/schemas/foo-1.2.3" in mapping
    assert b"http://somewhere.org/schemas/foo-1.2.3" in mapping["http://somewhere.org/schemas/foo-1.2.3"]


def test_directory_resource_mapping_with_traversable():
    """
    Confirm that DirectoryResourceMapping doesn't use pathlib.Path
    methods outside of the Traversable interface.
    """
    class MockTraversable(importlib_resources.abc.Traversable):
        def __init__(self, name, value):
            self._name = name
            self._value = value

        def iterdir(self):
            if isinstance(self._value, dict):
                for key, child in self._value.items():
                    yield MockTraversable(key, child)

        def read_bytes(self):
            if not isinstance(self._value, bytes):
                raise RuntimeError("Not a file")
            return self._value

        def read_text(self, encoding="utf-8"):
            return self.read_bytes().decode(encoding)

        def is_dir(self):
            return isinstance(self._value, dict)

        def is_file(self):
            return self._value is not None and not isinstance(self._value, dict)

        def joinpath(self, child):
            if isinstance(self._value, dict):
                child_value = self._value.get(child)
            else:
                child_value = None

            return MockTraversable(child, child_value)

        def __truediv__(self, child):
            return self.joinpath(child)

        def open(self, mode="r", *args, **kwargs):
            if not self.is_file():
                raise RuntimeError("Not a file")

            if mode == "r":
                return io.TextIOWrapper(io.BytesIO(self._value), *args, **kwargs)
            elif mode == "rb":
                return io.BytesIO(self._value)
            else:
                raise "Not a valid mode"

        @property
        def name(self):
            return self._name

    root = MockTraversable("/path/to/some/root", {
        "foo-1.0.0.yaml": b"foo",
        "bar-1.0.0.yaml": b"bar",
        "baz-1.0.0": b"baz",
        "nested": {
            "foz-1.0.0.yaml": b"foz"
        }
    })

    mapping = DirectoryResourceMapping(root, "http://somewhere.org/schemas")
    assert len(mapping) == 2
    assert set(mapping) == {"http://somewhere.org/schemas/foo-1.0.0", "http://somewhere.org/schemas/bar-1.0.0"}
    assert "http://somewhere.org/schemas/foo-1.0.0" in mapping
    assert mapping["http://somewhere.org/schemas/foo-1.0.0"] == b"foo"
    assert "http://somewhere.org/schemas/bar-1.0.0" in mapping
    assert mapping["http://somewhere.org/schemas/bar-1.0.0"] == b"bar"
    assert "http://somewhere.org/schemas/baz-1.0.0" not in mapping
    assert "http://somewhere.org/schemas/nested/foz-1.0.0" not in mapping

    mapping = DirectoryResourceMapping(root, "http://somewhere.org/schemas", recursive=True)
    assert len(mapping) == 3
    assert set(mapping) == {
        "http://somewhere.org/schemas/foo-1.0.0",
        "http://somewhere.org/schemas/bar-1.0.0",
        "http://somewhere.org/schemas/nested/foz-1.0.0"
    }
    assert "http://somewhere.org/schemas/foo-1.0.0" in mapping
    assert mapping["http://somewhere.org/schemas/foo-1.0.0"] == b"foo"
    assert "http://somewhere.org/schemas/bar-1.0.0" in mapping
    assert mapping["http://somewhere.org/schemas/bar-1.0.0"] == b"bar"
    assert "http://somewhere.org/schemas/baz-1.0.0" not in mapping
    assert "http://somewhere.org/schemas/nested/foz-1.0.0" in mapping
    assert mapping["http://somewhere.org/schemas/nested/foz-1.0.0"] == b"foz"

    mapping = DirectoryResourceMapping(root, "http://somewhere.org/schemas", filename_pattern="baz-*", stem_filename=False)
    assert len(mapping) == 1
    assert set(mapping) == {"http://somewhere.org/schemas/baz-1.0.0"}
    assert "http://somewhere.org/schemas/foo-1.0.0" not in mapping
    assert "http://somewhere.org/schemas/bar-1.0.0" not in mapping
    assert "http://somewhere.org/schemas/baz-1.0.0" in mapping
    assert mapping["http://somewhere.org/schemas/baz-1.0.0"] == b"baz"
    assert "http://somewhere.org/schemas/nested/foz-1.0.0" not in mapping


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

    with pytest.raises(KeyError, match="http://somewhere.org/schemas/missing-1.0.0"):
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


@pytest.mark.parametrize("uri", [
    "http://json-schema.org/draft-04/schema",
    "http://stsci.edu/schemas/yaml-schema/draft-01",
    "http://stsci.edu/schemas/asdf/core/asdf-1.1.0",
])
def test_get_core_resource_mappings(uri):
    mappings = get_core_resource_mappings()

    mapping = next(m for m in mappings if uri in m)
    assert mapping is not None

    assert uri.encode("utf-8") in mapping[uri]


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

    with pytest.raises(TypeError):
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
