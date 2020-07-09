import pytest

from asdf import resource


def test_traversable_resource_mapping(tmpdir):
    tmpdir.mkdir("schemas")
    (tmpdir/"schemas").mkdir("nested")
    with (tmpdir/"schemas"/"foo-1.2.3.yaml").open("w") as f:
        f.write("id: http://somewhere.org/schemas/foo-1.2.3\n")
    with (tmpdir/"schemas"/"nested"/"bar-4.5.6.yaml").open("w") as f:
        f.write("id: http://somewhere.org/schemas/nested/bar-4.5.6\n")
    with (tmpdir/"schemas"/"baz-7.8.9").open("w") as f:
        f.write("id: http://somewhere.org/schemas/baz-7.8.9\n")

    mapping = resource.TraversableResourceMapping(str(tmpdir/"schemas"), "http://somewhere.org/schemas")
    assert len(mapping) == 1
    assert set(mapping) == {"http://somewhere.org/schemas/foo-1.2.3"}
    assert "http://somewhere.org/schemas/foo-1.2.3" in mapping
    assert b"http://somewhere.org/schemas/foo-1.2.3" in mapping["http://somewhere.org/schemas/foo-1.2.3"]
    assert "http://somewhere.org/schemas/baz-7.8.9" not in mapping
    assert "http://somewhere.org/schemas/baz-7.8" not in mapping
    assert "http://somewhere.org/schemas/foo-1.2.3.yaml" not in mapping
    assert "http://somewhere.org/schemas/nested/bar-4.5.6" not in mapping

    mapping = resource.TraversableResourceMapping(str(tmpdir/"schemas"), "http://somewhere.org/schemas", recursive=True)
    assert len(mapping) == 2
    assert set(mapping) == {"http://somewhere.org/schemas/foo-1.2.3", "http://somewhere.org/schemas/nested/bar-4.5.6"}
    assert "http://somewhere.org/schemas/foo-1.2.3" in mapping
    assert b"http://somewhere.org/schemas/foo-1.2.3" in mapping["http://somewhere.org/schemas/foo-1.2.3"]
    assert "http://somewhere.org/schemas/baz-7.8.9" not in mapping
    assert "http://somewhere.org/schemas/baz-7.8" not in mapping
    assert "http://somewhere.org/schemas/nested/bar-4.5.6" in mapping
    assert b"http://somewhere.org/schemas/nested/bar-4.5.6" in mapping["http://somewhere.org/schemas/nested/bar-4.5.6"]

    mapping = resource.TraversableResourceMapping(
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


def test_resource_manager():
    mapping1 = {
        "http://somewhere.org/schemas/foo-1.0.0": b"foo",
        "http://somewhere.org/schemas/bar-1.0.0": b"bar",
    }
    mapping2 = {
        "http://somewhere.org/schemas/foo-1.0.0": b"foo override",
        "http://somewhere.org/schemas/baz-1.0.0": b"baz",
        "http://somewhere.org/schemas/foz-1.0.0": "foz",
    }
    manager = resource.ResourceManager([mapping1, mapping2])

    assert len(manager) == 4
    assert set(manager) == {
        "http://somewhere.org/schemas/foo-1.0.0",
        "http://somewhere.org/schemas/bar-1.0.0",
        "http://somewhere.org/schemas/baz-1.0.0",
        "http://somewhere.org/schemas/foz-1.0.0",
    }
    assert "http://somewhere.org/schemas/foo-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/foo-1.0.0"] == b"foo override"
    assert "http://somewhere.org/schemas/bar-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/bar-1.0.0"] == b"bar"
    assert "http://somewhere.org/schemas/baz-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/baz-1.0.0"] == b"baz"
    assert "http://somewhere.org/schemas/foz-1.0.0" in manager
    assert manager["http://somewhere.org/schemas/foz-1.0.0"] == b"foz"

    with pytest.raises(KeyError, match="http://somewhere.org/schemas/missing-1.0.0"):
        manager["http://somewhere.org/schemas/missing-1.0.0"]


def test_jsonschema_resource_mapping():
    mapping = resource.JsonschemaResourceMapping()
    assert len(mapping) == 1
    assert set(mapping) == {"http://json-schema.org/draft-04/schema"}
    assert "http://json-schema.org/draft-04/schema" in mapping
    assert b"http://json-schema.org/draft-04/schema" in mapping["http://json-schema.org/draft-04/schema"]


@pytest.mark.parametrize("uri", [
    "http://json-schema.org/draft-04/schema",
    "http://stsci.edu/schemas/yaml-schema/draft-01",
    "http://stsci.edu/schemas/asdf/core/asdf-1.1.0",
])
def test_get_core_resource_mappings(uri):
    mappings = resource.get_core_resource_mappings()

    mapping = next(m for m in mappings if uri in m)
    assert mapping is not None

    assert uri.encode("utf-8") in mapping[uri]
