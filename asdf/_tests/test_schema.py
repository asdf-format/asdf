import contextlib
import io
from datetime import datetime

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import asdf
from asdf import config_context, constants, get_config, schema, tagged, util, yamlutil
from asdf.exceptions import AsdfConversionWarning, AsdfWarning, ValidationError
from asdf.extension import TagDefinition
from asdf.testing.helpers import yaml_to_asdf


@contextlib.contextmanager
def tag_reference_extension():
    class TagReference:
        def __init__(self, name, things):
            self.name = name
            self.things = things

    tag_uri = "tag:nowhere.org:custom/tag_reference-1.0.0"
    schema_uri = "http://nowhere.org/schemas/custom/tag_reference-1.0.0"
    tag_def = asdf.extension.TagDefinition(tag_uri, schema_uris=schema_uri)

    class TagReferenceConverter:
        tags = [tag_uri]
        types = [TagReference]

        def to_yaml_tree(self, obj, tag, ctx):
            return {"name": obj.name, "things": obj.things}

        def from_yaml_tree(self, node, tag, ctx):
            return TagReference(node["name"], node["things"])

    class TagReferenceExtension:
        tags = [tag_def]
        extension_uri = "asdf://nowhere.org/extensions/tag_reference-1.0.0"
        converters = [TagReferenceConverter()]

    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: {schema_uri}
title: An example custom type for testing tag references

type: object
properties:
  name:
    type: string
  things:
    $ref: "http://stsci.edu/schemas/asdf/core/ndarray-1.1.0"
required: [name, things]
...
    """

    with config_context() as cfg:
        cfg.add_resource_mapping({schema_uri: tag_schema})
        cfg.add_extension(TagReferenceExtension())
        yield


def test_tagging_scalars():
    class Scalar:
        def __init__(self, value):
            self.value = value

    scalar_tag = "http://somewhere.org/tags/scalar-1.0.0"

    class ScalarConverter:
        tags = [scalar_tag]
        types = [Scalar]

        def to_yaml_tree(self, obj, tag, ctx):
            return obj.value

        def from_yaml_tree(self, node, tag, ctx):
            return Scalar(node)

    class ScalarExtension:
        tags = [scalar_tag]
        converters = [ScalarConverter()]
        extension_uri = "http://somewhere.org/extensions/scalar-1.0.0"

    yaml = f"""
tagged: !<{scalar_tag}>
  m
not_tagged:
  m
    """
    with asdf.config_context() as cfg:
        cfg.add_extension(ScalarExtension())
        buff = yaml_to_asdf(yaml)
        with asdf.open(buff) as ff:
            assert isinstance(ff.tree["tagged"], Scalar)
            assert not isinstance(ff.tree["not_tagged"], Scalar)
            assert isinstance(ff.tree["not_tagged"], str)

            assert ff.tree["tagged"].value == "m"
            assert ff.tree["not_tagged"] == "m"


def test_read_json_schema(test_data_path):
    """Pytest to make sure reading JSON schemas succeeds.

    This was known to fail on Python 3.5 See issue #314 at
    https://github.com/asdf-format/asdf/issues/314 for more details.
    """
    json_schema = test_data_path / "example_schema.json"
    schema_tree = schema.load_schema(json_schema, resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema(tmp_path):
    schema_def = """
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.1.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "../core/ndarray-1.1.0"

required: [foobar]
...
    """
    schema_path = tmp_path / "nugatory.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_file_url(tmp_path):
    schema_def = """
%YAML 1.1
%TAG !asdf! tag:stsci.edu:asdf/
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.1.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "http://stsci.edu/schemas/asdf/core/ndarray-1.1.0"

required: [foobar]
...
    """
    schema_path = tmp_path / "nugatory.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_asdf_uri_scheme():
    subschema_content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.1.0
id: asdf://somewhere.org/schemas/bar

bar:
  type: string
...
"""
    content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.1.0
id: asdf://somewhere.org/schemas/foo

definitions:
  local_bar:
    type: string

type: object
properties:
  bar:
    $ref: asdf://somewhere.org/schemas/bar#/bar
  local_bar:
    $ref: '#/definitions/local_bar'
...
"""
    with asdf.config_context() as config:
        config.add_resource_mapping({"asdf://somewhere.org/schemas/foo": content})
        config.add_resource_mapping({"asdf://somewhere.org/schemas/bar": subschema_content})

        schema_tree = schema.load_schema("asdf://somewhere.org/schemas/foo")
        instance = {"bar": "baz", "local_bar": "foz"}
        schema.validate(instance, schema=schema_tree)
        with pytest.raises(ValidationError, match=r".* is not of type .*"):
            schema.validate({"bar": 12}, schema=schema_tree)


def test_load_schema_with_stsci_id():
    """
    This tests the following edge case:
    - schema references a subschema provided by the new extension API
    - subschema URI shares a prefix with one of the old-style extension resolvers
    - resolve_references is enabled

    If we're not careful, the old-style resolver will mangle the URI and
    we won't be able to retrieve the schema content.
    """
    subschema_content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.1.0
id: http://stsci.edu/schemas/bar

bar:
  type: string
...
"""
    content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.1.0
id: http://stsci.edu/schemas/foo

definitions:
  local_bar:
    type: string

type: object
properties:
  bar:
    $ref: http://stsci.edu/schemas/bar#/bar
  local_bar:
    $ref: '#/definitions/local_bar'
...
"""
    with asdf.config_context() as config:
        config.add_resource_mapping({"http://stsci.edu/schemas/foo": content})
        config.add_resource_mapping({"http://stsci.edu/schemas/bar": subschema_content})

        schema_tree = schema.load_schema("http://stsci.edu/schemas/foo", resolve_references=True)
        instance = {"bar": "baz", "local_bar": "foz"}
        schema.validate(instance, schema=schema_tree)
        with pytest.raises(ValidationError, match=r".* is not of type .*"):
            schema.validate({"bar": 12}, schema=schema_tree)


def test_schema_caching():
    # Make sure that if we request the same URL, we get a different object
    # (despite the caching internal to load_schema).  Changes to a schema
    # dict should not impact other uses of that schema.

    s1 = schema.load_schema("http://stsci.edu/schemas/asdf/core/asdf-1.0.0")
    s2 = schema.load_schema("http://stsci.edu/schemas/asdf/core/asdf-1.0.0")
    assert s1 is not s2


def test_load_schema_from_resource_mapping():
    content = b"""
id: http://somewhere.org/schemas/razmataz-1.0.0
type: object
properties:
  foo:
    type: string
  bar:
    type: boolean
"""

    get_config().add_resource_mapping({"http://somewhere.org/schemas/razmataz-1.0.0": content})

    s = schema.load_schema("http://somewhere.org/schemas/razmataz-1.0.0")

    assert s["id"] == "http://somewhere.org/schemas/razmataz-1.0.0"


def test_flow_style():
    class CustomFlow:
        def __init__(self, a, b):
            self.a = a
            self.b = b

    tag_uri = "http://nowhere.org/tags/custom/custom_flow-1.0.0"

    class CustomFlowConverter:
        tags = [tag_uri]
        types = [CustomFlow]

        def to_yaml_tree(self, obj, tag, ctx):
            return {"a": obj.a, "b": obj.b}

        def from_yaml_tree(self, node, tag, ctx):
            return CustomFlow(node["a"], node["b"])

    schema_uri = "http://nowhere.org/schemas/custom/custom_flow-1.0.0"
    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: "{schema_uri}"
type: object
properties:
  a:
    type: number
  b:
    type: number
flowStyle: block
    """

    tag_def = TagDefinition(tag_uri, schema_uris=[schema_uri])

    class CustomFlowExtension:
        extension_uri = "http://nowhere.org/extensions/custom/custom_flow-1.0.0"
        tags = [tag_def]
        converters = [CustomFlowConverter()]

    with config_context() as cfg:
        cfg.add_extension(CustomFlowExtension())
        cfg.add_resource_mapping({schema_uri: tag_schema})
        buff = io.BytesIO()
        ff = asdf.AsdfFile({"custom_flow": CustomFlow(42, 43)})
        ff.write_to(buff)

        assert b"  a: 42\n  b: 43" in buff.getvalue()


def test_style():
    class CustomStyle:
        def __init__(self, message):
            self.message = message

    tag_uri = "http://nowhere.org/tags/custom/custom_style-1.0.0"

    class CustomStyleConverter:
        tags = [tag_uri]
        types = [CustomStyle]

        def to_yaml_tree(self, obj, tag, ctx):
            return obj.message

        def from_yaml_tree(self, node, tag, ctx):
            return CustomStyle(node)

    schema_uri = "http://nowhere.org/schemas/custom/custom_style-1.0.0"
    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: "{schema_uri}"
type: string
style: literal
    """

    tag_def = TagDefinition(tag_uri, schema_uris=[schema_uri])

    class CustomStyleExtension:
        extension_uri = "http://nowhere.org/extensions/custom/custom_style-1.0.0"
        tags = [tag_def]
        converters = [CustomStyleConverter()]

    with config_context() as cfg:
        cfg.add_extension(CustomStyleExtension())
        cfg.add_resource_mapping({schema_uri: tag_schema})

        tree = {"custom_style": CustomStyle("short")}

        buff = io.BytesIO()
        ff = asdf.AsdfFile(tree)
        ff.write_to(buff)

        assert b"|-\n  short\n" in buff.getvalue()


def test_property_order():
    tree = {"foo": np.ndarray([1, 2, 3])}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    ndarray_schema = schema.load_schema("http://stsci.edu/schemas/asdf/core/ndarray-1.1.0")
    property_order = ndarray_schema["anyOf"][1]["propertyOrder"]

    last_index = 0
    for prop in property_order:
        index = buff.getvalue().find(prop.encode("utf-8") + b":")
        if index != -1:
            assert index > last_index
            last_index = index


def test_invalid_nested():
    tag_uri = "http://nowhere.org/tags/custom/custom-1.0.0"
    schema_uri = "http://nowhere.org/schemas/custom/custom-1.0.0"
    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: "{schema_uri}"
type: integer
default: 42
    """

    class Custom:
        def __init__(self, value):
            self.value = value

    class CustomConverter:
        tags = [tag_uri]
        types = [Custom]

        def to_yaml_tree(self, obj, tag, ctx):
            return obj.value

        def from_yaml_tree(self, node, tag, ctx):
            return Custom(node)

    tag_def = TagDefinition(tag_uri, schema_uris=[schema_uri])

    class CustomExtension:
        extension_uri = "http://nowhere.org/extensions/custom/custom-1.0.0"
        tags = [tag_def]
        converters = [CustomConverter()]

    yaml = f"""
custom: !<{tag_uri}>
  foo
    """
    buff = yaml_to_asdf(yaml)
    # This should cause a warning but not an error because without explicitly
    # providing an extension, our custom type will not be recognized and will
    # simply be converted to a raw type.
    with pytest.warns(AsdfConversionWarning, match=tag_uri):
        with asdf.open(buff) as af:
            af["custom"]

    buff.seek(0)
    with config_context() as cfg:
        cfg.add_extension(CustomExtension())
        cfg.add_resource_mapping({schema_uri: tag_schema})
        with (
            pytest.raises(ValidationError, match=r".* is not of type .*"),
            asdf.open(
                buff,
            ),
        ):
            pass

        # Make sure tags get validated inside of other tags that know
        # nothing about them.
        yaml = f"""
array: !core/ndarray-1.1.0
  data: [0, 1, 2]
  custom: !<{tag_uri}>
    foo
        """
        buff = yaml_to_asdf(yaml)
        with (
            pytest.raises(ValidationError, match=r".* is not of type .*"),
            asdf.open(
                buff,
            ),
        ):
            pass


def test_invalid_schema():
    s = {"type": "integer"}
    schema.check_schema(s)

    s = {"type": "foobar"}
    with pytest.raises(ValidationError, match=r".* is not valid under any of the given schemas.*"):
        schema.check_schema(s)


def test_defaults():
    s = {"type": "object", "properties": {"a": {"type": "integer", "default": 42}}}

    t = {}

    cls = schema._create_validator(schema.FILL_DEFAULTS)
    validator = cls(s)
    validator.validate(t)

    assert t["a"] == 42

    cls = schema._create_validator(schema.REMOVE_DEFAULTS)
    validator = cls(s)
    validator.validate(t)

    assert t == {}


def test_default_check_in_schema():
    s = {"type": "object", "properties": {"a": {"type": "integer", "default": "foo"}}}

    with pytest.raises(ValidationError, match=r".* is not of type .*"):
        schema.check_schema(s)

    schema.check_schema(s, validate_default=False)


def test_check_complex_default():
    default_software = tagged.TaggedDict({"name": "asdf", "version": "2.7.0"}, "tag:stsci.edu/asdf/core/software-1.0.0")

    s = {
        "type": "object",
        "properties": {
            "a": {"type": "object", "tag": "tag:stsci.edu/asdf/core/software-1.0.0", "default": default_software},
        },
    }

    schema.check_schema(s)

    s["properties"]["a"]["tag"] = "tag:stsci.edu/asdf/core/ndarray-1.1.0"
    with pytest.raises(ValidationError, match=r"mismatched tags, wanted .*, got .*"):
        schema.check_schema(s)


def test_fill_and_remove_defaults():
    tag_uri = "http://nowhere.org/tags/custom/default-1.0.0"
    schema_uri = "http://nowhere.org/schemas/custom/default-1.0.0"
    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: "{schema_uri}"
type: object
properties:
  a:
    type: integer
    default: 42
  b:
    type: object
    properties:
      c:
        type: integer
        default: 82
  d:
    allOf:
      - type: object
        properties:
          e:
            type: integer
            default: 122
      - type: object
        properties:
          f:
            type: integer
            default: 162
  g:
    anyOf:
      - type: object
        properties:
          h:
            type: integer
            default: 202
      - type: object
        properties:
          i:
            type: integer
            default: 242
  j:
    oneOf:
      - type: object
        properties:
          k:
            type: integer
            default: 282
        required: [k]
        additionalProperties: false
      - type: object
        properties:
          l:
            type: integer
            default: 322
        required: [l]
        additionalProperties: false
    """

    class Default(dict):
        pass

    class DefaultConverter:
        tags = [tag_uri]
        types = [Default]

        def to_yaml_tree(self, obj, tag, ctx):
            return dict(obj)

        def from_yaml_tree(self, node, tag, ctx):
            return Default(**node)

    tag_def = TagDefinition(tag_uri, schema_uris=[schema_uri])

    class DefaultExtension:
        tags = [tag_def]
        converters = [DefaultConverter()]
        extension_uri = "http://nowhere.org/extensions/custom/default-1.0.0"

    with config_context() as cfg:
        # later versions do not fill defaults
        cfg.default_version = "1.5.0"
        cfg.add_extension(DefaultExtension())
        cfg.add_resource_mapping({schema_uri: tag_schema})
        yaml = """
custom: !<http://nowhere.org/tags/custom/default-1.0.0>
  b: {}
  d: {}
  g: {}
  j:
    l: 362
        """
        buff = yaml_to_asdf(yaml, version="1.5.0")
        with asdf.open(buff) as ff:
            assert "a" in ff.tree["custom"]
            assert ff.tree["custom"]["a"] == 42
            assert ff.tree["custom"]["b"]["c"] == 82
            # allOf combiner should fill defaults from all subschemas:
            assert ff.tree["custom"]["d"]["e"] == 122
            assert ff.tree["custom"]["d"]["f"] == 162
            # anyOf combiners should be ignored:
            assert "h" not in ff.tree["custom"]["g"]
            assert "i" not in ff.tree["custom"]["g"]
            # oneOf combiners should be ignored:
            assert "k" not in ff.tree["custom"]["j"]
            assert ff.tree["custom"]["j"]["l"] == 362

        buff.seek(0)
        with config_context() as config:
            config.legacy_fill_schema_defaults = False
            with asdf.open(buff) as ff:
                assert "a" not in ff.tree["custom"]
                assert "c" not in ff.tree["custom"]["b"]
                assert "e" not in ff.tree["custom"]["d"]
                assert "f" not in ff.tree["custom"]["d"]
                assert "h" not in ff.tree["custom"]["g"]
                assert "i" not in ff.tree["custom"]["g"]
                assert "k" not in ff.tree["custom"]["j"]
                assert ff.tree["custom"]["j"]["l"] == 362
                ff.fill_defaults()
                assert "a" in ff.tree["custom"]
                assert ff.tree["custom"]["a"] == 42
                assert "c" in ff.tree["custom"]["b"]
                assert ff.tree["custom"]["b"]["c"] == 82
                assert ff.tree["custom"]["b"]["c"] == 82
                assert ff.tree["custom"]["d"]["e"] == 122
                assert ff.tree["custom"]["d"]["f"] == 162
                assert "h" not in ff.tree["custom"]["g"]
                assert "i" not in ff.tree["custom"]["g"]
                assert "k" not in ff.tree["custom"]["j"]
                assert ff.tree["custom"]["j"]["l"] == 362
                ff.remove_defaults()
                assert "a" not in ff.tree["custom"]
                assert "c" not in ff.tree["custom"]["b"]
                assert "e" not in ff.tree["custom"]["d"]
                assert "f" not in ff.tree["custom"]["d"]
                assert "h" not in ff.tree["custom"]["g"]
                assert "i" not in ff.tree["custom"]["g"]
                assert "k" not in ff.tree["custom"]["j"]
                assert ff.tree["custom"]["j"]["l"] == 362


def test_one_of():
    """
    Covers https://github.com/asdf-format/asdf/issues/809
    """

    class OneOf:
        def __init__(self, value):
            self.value = value

    tag_uri = "http://nowhere.org/custom/one_of-1.0.0"

    class OneOfConverter:
        tags = [tag_uri]
        types = [OneOf]

        def to_yaml_tree(self, obj, tag, ctx):
            return {"value": obj.value}

        def from_yaml_tree(self, node, tag, ctx):
            return OneOf(node["value"])

    schema_uri = "http://nowhere.org/schemas/custom/one_of-1.0.0"
    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: "{schema_uri}"
title: |
  oneOf test schema
oneOf:
  - type: object
    properties:
      value:
        type: number
    required: [value]
    additionalProperties: false

  - type: object
    properties:
      value:
        type: string
    required: [value]
    additionalProperties: false
...
    """

    tag_def = TagDefinition(tag_uri, schema_uris=[schema_uri])

    class OneOfExtension:
        extension_uri = "http://nowhere.org/extensions/custom/one_of-1.0.0"
        tags = [tag_def]
        converters = [OneOfConverter()]

    yaml = f"""
one_of: !<{tag_uri}>
  value: foo
    """

    with config_context() as cfg:
        cfg.add_extension(OneOfExtension())
        cfg.add_resource_mapping({schema_uri: tag_schema})

        buff = yaml_to_asdf(yaml)
        with asdf.open(buff) as ff:
            assert ff["one_of"].value == "foo"


def test_tag_reference_validation():
    yaml = """
custom: !<tag:nowhere.org:custom/tag_reference-1.0.0>
  name:
    "Something"
  things: !core/ndarray-1.1.0
    data: [1, 2, 3]
    """

    with tag_reference_extension():
        buff = yaml_to_asdf(yaml)
        with asdf.open(buff) as ff:
            custom = ff.tree["custom"]
            assert custom.name == "Something"
            assert_array_equal(custom.things, [1, 2, 3])


def test_foreign_tag_reference_validation():
    class ForeignTagReference:
        def __init__(self, a):
            self.a = a

    tag_uri = "tag:nowhere.org:custom/foreign_tag_reference-1.0.0"
    schema_uri = "http://nowhere.org/schemas/custom/foreign_tag_reference-1.0.0"
    tag_def = asdf.extension.TagDefinition(tag_uri, schema_uris=schema_uri)

    class ForeignTagReferenceConverter:
        tags = [tag_uri]
        types = [ForeignTagReference]

        def to_yaml_tree(self, obj, tag, ctx):
            return {"a": obj.a}

        def from_yaml_tree(self, node, tag, ctx):
            return ForeignTagReference(node["a"])

    class ForeignTagReferenceExtension:
        tags = [tag_def]
        extension_uri = "asdf://nowhere.org/extensions/foreign_tag_reference-1.0.0"
        converters = [ForeignTagReferenceConverter()]

    tag_schema = f"""
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
id: {schema_uri}
title: An example custom type for testing tag references

type: object
properties:
  a:
    # Test foreign tag reference using tag URI
    $ref: "http://nowhere.org/schemas/custom/tag_reference-1.0.0"
required: [a]
...
    """

    yaml = """
custom: !<tag:nowhere.org:custom/foreign_tag_reference-1.0.0>
  a: !<tag:nowhere.org:custom/tag_reference-1.0.0>
    name:
      "Something"
    things: !core/ndarray-1.1.0
      data: [1, 2, 3]
    """

    with tag_reference_extension():
        cfg = asdf.get_config()
        cfg.add_resource_mapping({schema_uri: tag_schema})
        cfg.add_extension(ForeignTagReferenceExtension())

        buff = yaml_to_asdf(yaml)
        with asdf.open(buff) as ff:
            a = ff.tree["custom"].a
            assert a.name == "Something"
            assert_array_equal(a.things, [1, 2, 3])


def test_self_reference_resolution(test_data_path):
    s = schema.load_schema(
        test_data_path / "self_referencing-1.0.0.yaml",
        resolve_references=True,
    )
    assert "$ref" not in repr(s)
    assert s["anyOf"][1] == s["anyOf"][0]


def test_schema_resolved_via_entry_points():
    """Test that entry points mappings to core schema works"""
    tag = "tag:stsci.edu:asdf/fits/fits-1.0.0"
    extension_manager = asdf.extension.get_cached_extension_manager(get_config().extensions)
    schema_uris = extension_manager.get_tag_definition(tag).schema_uris
    assert len(schema_uris) > 0
    s = schema.load_schema(schema_uris[0])
    assert s["id"] == schema_uris[0]


@pytest.mark.parametrize("num", [constants.MAX_NUMBER + 1, constants.MIN_NUMBER - 1])
def test_max_min_literals(num):
    msg = r"Integer value .* is too large to safely represent as a literal in ASDF"

    af = asdf.AsdfFile()
    af["test_int"] = num
    with pytest.raises(ValidationError, match=msg):
        af.validate()

    af = asdf.AsdfFile()
    af["test_list"] = [num]
    with pytest.raises(ValidationError, match=msg):
        af.validate()

    af = asdf.AsdfFile()
    af[num] = "test_key"
    with pytest.raises(ValidationError, match=msg):
        af.validate()


@pytest.mark.parametrize("num", [constants.MAX_NUMBER + 1, constants.MIN_NUMBER - 1])
@pytest.mark.parametrize("ttype", ["val", "list", "key"])
def test_max_min_literals_write(num, ttype, tmp_path):
    outfile = tmp_path / "test.asdf"
    af = asdf.AsdfFile()

    # Validation doesn't occur here, so no warning/error will be raised.
    if ttype == "val":
        af.tree["test_int"] = num
    elif ttype == "list":
        af.tree["test_int"] = [num]
    else:
        af.tree[num] = "test_key"

    # Validation will occur on write, though, so detect it.
    msg = r"Integer value .* is too large to safely represent as a literal in ASDF"
    with pytest.raises(ValidationError, match=msg):
        af.write_to(outfile)
    af.close()


@pytest.mark.parametrize("value", [constants.MAX_NUMBER + 1, constants.MIN_NUMBER - 1])
def test_read_large_literal(value):
    yaml = f"integer: {value}"

    buff = yaml_to_asdf(yaml)

    with pytest.warns(AsdfWarning, match=r"Invalid integer literal value"), asdf.open(buff) as af:
        assert af["integer"] == value

    yaml = f"{value}: foo"

    buff = yaml_to_asdf(yaml)

    with pytest.warns(AsdfWarning, match=r"Invalid integer literal value"), asdf.open(buff) as af:
        assert af[value] == "foo"


@pytest.mark.parametrize(
    ("version", "keys"),
    [
        ("1.6.0", ["foo", 42, True]),
        ("1.5.0", ["foo", 42, True, 3.14159, datetime.now(), b"foo", None]),
    ],
)
def test_mapping_supported_key_types(keys, version):
    for key in keys:
        af = asdf.AsdfFile({key: "value"}, version=version)
        buff = io.BytesIO()
        af.write_to(buff)
        buff.seek(0)
        with asdf.open(buff) as af:
            assert af[key] == "value"


@pytest.mark.parametrize(
    ("version", "keys"),
    [
        ("1.6.0", [3.14159, datetime.now(), b"foo", None, ("foo", "bar")]),
    ],
)
def test_mapping_unsupported_key_types(keys, version):
    for key in keys:
        af = asdf.AsdfFile(version=version)
        af[key] = "value"
        with pytest.raises(ValidationError, match=r"Mapping key .* is not permitted"):
            af.validate()


def test_nested_array():
    s = {
        "type": "object",
        "properties": {
            "stuff": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": [
                        {"type": "integer"},
                        {"type": "string"},
                        {"type": "number"},
                    ],
                    "minItems": 3,
                    "maxItems": 3,
                },
            },
        },
    }

    good = {"stuff": [[1, "hello", 2], [4, "world", 9.7]]}
    schema.validate(good, schema=s)

    bads = [
        {"stuff": [[1, 2, 3]]},
        {"stuff": [12, "dldl"]},
        {"stuff": [[12, "dldl"]]},
        {"stuff": [[1, "hello", 2], [4, 5]]},
        {"stuff": [[1, "hello", 2], [4, 5, 6]]},
    ]

    for b in bads:
        with pytest.raises(ValidationError, match=r"[.* is not of type .*, .* is too short]"):
            schema.validate(b, schema=s)


def test_nested_array_yaml(tmp_path):
    schema_def = """
%YAML 1.1
---
type: object
properties:
  stuff:
    type: array
    items:
      type: array
      items:
        - type: integer
        - type: string
        - type: number
      minItems: 3
      maxItems: 3
...
    """
    schema_path = tmp_path / "nested.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path))
    schema.check_schema(schema_tree)

    good = {"stuff": [[1, "hello", 2], [4, "world", 9.7]]}
    schema.validate(good, schema=schema_tree)

    bads = [
        {"stuff": [[1, 2, 3]]},
        {"stuff": [12, "dldl"]},
        {"stuff": [[12, "dldl"]]},
        {"stuff": [[1, "hello", 2], [4, 5]]},
        {"stuff": [[1, "hello", 2], [4, 5, 6]]},
    ]

    for b in bads:
        with pytest.raises(ValidationError, match=r"[.* is not of type .*, .* is too short]"):
            schema.validate(b, schema=schema_tree)


@pytest.mark.parametrize(
    ("numpy_value", "valid_types"),
    [
        (np.str_("foo"), {"string"}),
        (np.bytes_("foo"), set()),
        (np.float16(3.14), {"number"}),
        (np.float32(3.14159), {"number"}),
        (np.float64(3.14159), {"number"}),
        # Evidently float128 is not available on Windows:
        (getattr(np, "float128", np.float64)(3.14159), {"number"}),
        (np.int8(42), {"number", "integer"}),
        (np.int16(42), {"number", "integer"}),
        (np.int32(42), {"number", "integer"}),
        (np.longlong(42), {"number", "integer"}),
        (np.uint8(42), {"number", "integer"}),
        (np.uint16(42), {"number", "integer"}),
        (np.uint32(42), {"number", "integer"}),
        (np.uint64(42), {"number", "integer"}),
        (np.ulonglong(42), {"number", "integer"}),
    ],
)
def test_numpy_scalar_type_validation(numpy_value, valid_types):
    def _assert_validation(jsonschema_type, expected_valid):
        validator = schema.get_validator(schema={"type": jsonschema_type})
        try:
            validator.validate(numpy_value)
        except ValidationError:
            valid = False
        else:
            valid = True

        if valid is not expected_valid:
            description = "valid" if expected_valid else "invalid"
            msg = (
                f"Expected numpy.{type(numpy_value).__name__} "
                f"to be {description} against jsonschema type "
                f"'{jsonschema_type}'"
            )
            raise AssertionError(msg)

    for jsonschema_type in valid_types:
        _assert_validation(jsonschema_type, True)

    invalid_types = {"string", "number", "integer", "boolean", "null", "object"} - valid_types
    for jsonschema_type in invalid_types:
        _assert_validation(jsonschema_type, False)


def test_validator_visit_repeat_nodes():
    ctx = asdf.AsdfFile()
    node = asdf.tags.core.Software(name="Minesweeper")
    tree = yamlutil.custom_tree_to_tagged_tree({"node": node, "other_node": node, "nested": {"node": node}}, ctx)

    visited_nodes = []

    def _test_validator(validator, value, instance, schema):
        visited_nodes.append(instance)

    validator = schema.get_validator(ctx=ctx, validators=util.HashableDict(type=_test_validator))
    validator.validate(tree)
    assert len(visited_nodes) == 1

    visited_nodes.clear()
    validator = schema.get_validator(validators=util.HashableDict(type=_test_validator), _visit_repeat_nodes=True)
    validator.validate(tree)
    assert len(visited_nodes) == 3


def test_tag_validator():
    content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.1.0
id: asdf://somewhere.org/schemas/foo
tag: asdf://somewhere.org/tags/foo
...
"""
    with asdf.config_context() as config:
        config.add_resource_mapping({"asdf://somewhere.org/schemas/foo": content})

        schema_tree = schema.load_schema("asdf://somewhere.org/schemas/foo")
        instance = tagged.TaggedDict(tag="asdf://somewhere.org/tags/foo")
        schema.validate(instance, schema=schema_tree)
        with pytest.raises(ValidationError, match=r"mismatched tags, wanted .*, got .*"):
            schema.validate(tagged.TaggedDict(tag="asdf://somewhere.org/tags/bar"), schema=schema_tree)

    content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.1.0
id: asdf://somewhere.org/schemas/bar
tag: asdf://somewhere.org/tags/bar-*
...
"""
    with asdf.config_context() as config:
        config.add_resource_mapping({"asdf://somewhere.org/schemas/bar": content})

        schema_tree = schema.load_schema("asdf://somewhere.org/schemas/bar")
        instance = tagged.TaggedDict(tag="asdf://somewhere.org/tags/bar-2.5")
        schema.validate(instance, schema=schema_tree)
        with pytest.raises(ValidationError, match=r"mismatched tags, wanted .*, got .*"):
            schema.validate(tagged.TaggedDict(tag="asdf://somewhere.org/tags/foo-1.0"), schema=schema_tree)
