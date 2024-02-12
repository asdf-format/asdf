"""
Integration tests for the new plugin APIs.
"""

import pytest

import asdf
from asdf.extension import TagDefinition

FOO_SCHEMA_URI = "asdf://somewhere.org/extensions/foo/schemas/foo-1.0"
FOO_SCHEMA = f"""
id: {FOO_SCHEMA_URI}
type: object
properties:
  value:
    type: string
required: ["value"]
"""


class Foo:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class FooConverter:
    types = [Foo]
    tags = ["asdf://somewhere.org/extensions/foo/tags/foo-*"]

    def to_yaml_tree(self, obj, tag, ctx):
        return {"value": obj.value}

    def from_yaml_tree(self, obj, tag, ctx):
        return Foo(obj["value"])


class FooExtension:
    extension_uri = "asdf://somewhere.org/extensions/foo-1.0"
    converters = [FooConverter()]
    tags = [
        TagDefinition(
            "asdf://somewhere.org/extensions/foo/tags/foo-1.0",
            schema_uris=FOO_SCHEMA_URI,
        ),
    ]


def test_serialize_custom_type(tmp_path):
    with asdf.config_context() as config:
        config.add_resource_mapping({FOO_SCHEMA_URI: FOO_SCHEMA})
        config.add_extension(FooExtension())

        path = str(tmp_path / "test.asdf")

        af = asdf.AsdfFile()
        af["foo"] = Foo("bar")
        af.write_to(path)

        with asdf.open(path) as af2:
            assert af2["foo"].value == "bar"

        af["foo"] = Foo(12)
        with pytest.raises(asdf.ValidationError, match=r".* is not of type .*"):
            af.write_to(path)


FOOFOO_SCHEMA_URI = "asdf://somewhere.org/extensions/foo/schemas/foo_foo-1.0"
FOOFOO_SCHEMA = f"""
id: {FOOFOO_SCHEMA_URI}
type: object
properties:
  value_value:
    type: string
required: ["value_value"]
"""


class FooFoo(Foo):
    def __init__(self, value, value_value):
        super().__init__(value)

        self._value_value = value_value

    @property
    def value_value(self):
        return self._value_value


class FooFooConverter:
    types = [FooFoo]
    tags = ["asdf://somewhere.org/extensions/foo/tags/foo_foo-*"]

    def to_yaml_tree(self, obj, tag, ctx):
        return {"value": obj.value, "value_value": obj.value_value}

    def from_yaml_tree(self, obj, tag, ctx):
        return FooFoo(obj["value"], obj["value_value"])


class FooFooExtension:
    extension_uri = "asdf://somewhere.org/extensions/foo_foo-1.0"
    converters = [FooFooConverter()]
    tags = [
        TagDefinition(
            "asdf://somewhere.org/extensions/foo/tags/foo_foo-1.0",
            schema_uris=[FOO_SCHEMA_URI, FOOFOO_SCHEMA_URI],
        ),
    ]


def test_serialize_with_multiple_schemas(tmp_path):
    with asdf.config_context() as config:
        config.add_resource_mapping({FOO_SCHEMA_URI: FOO_SCHEMA, FOOFOO_SCHEMA_URI: FOOFOO_SCHEMA})
        config.add_extension(FooFooExtension())

        path = str(tmp_path / "test.asdf")

        af = asdf.AsdfFile()
        af["foo_foo"] = FooFoo("bar", "bar_bar")
        af.write_to(path)

        with asdf.open(path) as af2:
            assert af2["foo_foo"].value == "bar"
            assert af2["foo_foo"].value_value == "bar_bar"

        af["foo_foo"] = FooFoo(12, "bar_bar")
        with pytest.raises(asdf.ValidationError, match=r".* is not of type .*"):
            af.write_to(path)

        af["foo_foo"] = FooFoo("bar", 34)
        with pytest.raises(asdf.ValidationError, match=r".* is not of type .*"):
            af.write_to(path)


class FooFooConverterlessExtension:
    extension_uri = "asdf://somewhere.org/extensions/foo_foo-1.0"
    converters = []
    tags = [
        TagDefinition(
            "asdf://somewhere.org/extensions/foo/tags/foo_foo-1.0",
            schema_uris=[FOO_SCHEMA_URI, FOOFOO_SCHEMA_URI],
        ),
    ]


def test_converterless_serialize_with_multiple_schemas(tmp_path):
    with asdf.config_context() as config:
        config.add_resource_mapping({FOO_SCHEMA_URI: FOO_SCHEMA, FOOFOO_SCHEMA_URI: FOOFOO_SCHEMA})
        config.add_extension(FooFooConverterlessExtension())

        path = str(tmp_path / "test.asdf")

        af = asdf.AsdfFile()
        af["foo_foo"] = "asdf://somewhere.org/extensions/foo/tags/foo_foo-1.0 {bar: bar_bar}"
        af.write_to(path)

        with asdf.open(path) as af2:
            assert af2["foo_foo"] == af["foo_foo"]
