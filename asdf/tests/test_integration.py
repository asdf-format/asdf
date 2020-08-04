"""
Integration tests for the new plugin APIs.
"""
import pytest

import asdf
from asdf.extension import TagDefinition


FOO_SCHEMA_URI = "asdf://somewhere.org/extensions/foo/schemas/foo-1.0"
FOO_SCHEMA = """
id: {}
type: object
properties:
  value:
    type: string
required: ["value"]
""".format(FOO_SCHEMA_URI)


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
        return {
            "value": obj.value
        }

    def from_yaml_tree(self, obj, tag, ctx):
        return Foo(obj["value"])


class FooExtension:
    extension_uri = "asdf://somewhere.org/extensions/foo-1.0"
    converters = [FooConverter()]
    tags = [
        TagDefinition(
            "asdf://somewhere.org/extensions/foo/tags/foo-1.0",
            schema_uri=FOO_SCHEMA_URI,
        )
    ]


def test_serialize_custom_type(tmpdir):
    with asdf.config_context() as config:
        config.add_resource_mapping({FOO_SCHEMA_URI: FOO_SCHEMA})
        config.add_extension(FooExtension())

        path = str(tmpdir/"test.asdf")

        af = asdf.AsdfFile()
        af["foo"] = Foo("bar")
        af.write_to(path)

        with asdf.open(path) as af2:
            assert af2["foo"].value == "bar"

        with pytest.raises(asdf.ValidationError):
            af["foo"] = Foo(12)
            af.write_to(path)
