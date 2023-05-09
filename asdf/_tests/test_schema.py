import io
from datetime import datetime

import numpy as np
import pytest
from jsonschema import ValidationError
from numpy.testing import assert_array_equal

import asdf
import asdf.testing.helpers
from asdf import _resolver as resolver
from asdf import _types as types
from asdf import config_context, constants, extension, get_config, schema, tagged, util, yamlutil
from asdf._tests import _helpers as helpers
from asdf._tests.objects import CustomExtension
from asdf.exceptions import AsdfConversionWarning, AsdfDeprecationWarning, AsdfWarning

with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

    class TagReferenceType(types.CustomType):
        """
        This class is used by several tests below for validating foreign type
        references in schemas and ASDF files.
        """

        name = "tag_reference"
        organization = "nowhere.org"
        version = (1, 0, 0)
        standard = "custom"

        @classmethod
        def from_tree(cls, tree, ctx):
            node = {}
            node["name"] = tree["name"]
            node["things"] = tree["things"]
            return node


def test_tagging_scalars():
    pytest.importorskip("astropy", "3.0.0")
    from astropy import units as u

    yaml = """
unit: !unit/unit-1.0.0
  m
not_unit:
  m
    """
    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff) as ff:
        assert isinstance(ff.tree["unit"], u.UnitBase)
        assert not isinstance(ff.tree["not_unit"], u.UnitBase)
        assert isinstance(ff.tree["not_unit"], str)

        assert ff.tree == {"unit": u.m, "not_unit": "m"}


def test_read_json_schema():
    """Pytest to make sure reading JSON schemas succeeds.

    This was known to fail on Python 3.5 See issue #314 at
    https://github.com/asdf-format/asdf/issues/314 for more details.
    """
    json_schema = helpers.get_test_data_path("example_schema.json")
    schema_tree = schema.load_schema(json_schema, resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema(tmp_path):
    schema_def = """
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "../core/ndarray-1.0.0"

required: [foobar]
...
    """
    schema_path = tmp_path / "nugatory.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_full_tag(tmp_path):
    schema_def = """
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "tag:stsci.edu:asdf/core/ndarray-1.0.0"

required: [foobar]
...
    """
    schema_path = tmp_path / "nugatory.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_tag_address(tmp_path):
    schema_def = """
%YAML 1.1
%TAG !asdf! tag:stsci.edu:asdf/
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "http://stsci.edu/schemas/asdf/core/ndarray-1.0.0"

required: [foobar]
...
    """
    schema_path = tmp_path / "nugatory.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_file_url(tmp_path):
    with pytest.warns(AsdfDeprecationWarning, match="get_default_resolver is deprecated"):
        schema_def = """
%YAML 1.1
%TAG !asdf! tag:stsci.edu:asdf/
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "{}"

required: [foobar]
...
        """.format(
            extension.get_default_resolver()("tag:stsci.edu:asdf/core/ndarray-1.0.0"),
        )
    schema_path = tmp_path / "nugatory.yaml"
    schema_path.write_bytes(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_asdf_uri_scheme():
    subschema_content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.0.0
id: asdf://somewhere.org/schemas/bar

bar:
  type: string
...
"""
    content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.0.0
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
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.0.0
id: http://stsci.edu/schemas/bar

bar:
  type: string
...
"""
    content = """%YAML 1.1
---
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.0.0
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


def test_asdf_file_resolver_hashing():
    # Confirm that resolvers from distinct AsdfFile instances
    # hash to the same value (this allows schema caching to function).
    a1 = asdf.AsdfFile()
    a2 = asdf.AsdfFile()

    with pytest.warns(AsdfDeprecationWarning, match="AsdfFile.resolver is deprecated"):
        assert hash(a1.resolver) == hash(a2.resolver)
        assert a1.resolver == a2.resolver


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
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomFlowStyleType(dict, types.CustomType):
            name = "custom_flow"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

    class CustomFlowStyleExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowStyleType]

    tree = {"custom_flow": CustomFlowStyleType({"a": 42, "b": 43})}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, extensions=CustomFlowStyleExtension())
    ff.write_to(buff)

    assert b"  a: 42\n  b: 43" in buff.getvalue()


def test_style():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomStyleType(str, types.CustomType):
            name = "custom_style"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

    class CustomStyleExtension(CustomExtension):
        @property
        def types(self):
            return [CustomStyleType]

    tree = {"custom_style": CustomStyleType("short")}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, extensions=CustomStyleExtension())
    ff.write_to(buff)

    assert b"|-\n  short\n" in buff.getvalue()


def test_property_order():
    tree = {"foo": np.ndarray([1, 2, 3])}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    ndarray_schema = schema.load_schema("http://stsci.edu/schemas/asdf/core/ndarray-1.0.0")
    property_order = ndarray_schema["anyOf"][1]["propertyOrder"]

    last_index = 0
    for prop in property_order:
        index = buff.getvalue().find(prop.encode("utf-8") + b":")
        if index != -1:
            assert index > last_index
            last_index = index


def test_invalid_nested():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomType(str, types.CustomType):
            name = "custom"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

    class CustomTypeExtension(CustomExtension):
        @property
        def types(self):
            return [CustomType]

    yaml = """
custom: !<tag:nowhere.org:custom/custom-1.0.0>
  foo
    """
    buff = helpers.yaml_to_asdf(yaml)
    # This should cause a warning but not an error because without explicitly
    # providing an extension, our custom type will not be recognized and will
    # simply be converted to a raw type.
    with pytest.warns(AsdfConversionWarning, match=r"tag:nowhere.org:custom/custom-1.0.0"), asdf.open(buff):
        pass

    buff.seek(0)
    with pytest.raises(ValidationError, match=r".* is not of type .*"), asdf.open(
        buff,
        extensions=[CustomTypeExtension()],
    ):
        pass

    # Make sure tags get validated inside of other tags that know
    # nothing about them.
    yaml = """
array: !core/ndarray-1.0.0
  data: [0, 1, 2]
  custom: !<tag:nowhere.org:custom/custom-1.0.0>
    foo
    """
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.raises(ValidationError, match=r".* is not of type .*"), asdf.open(
        buff,
        extensions=[CustomTypeExtension()],
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

    s["properties"]["a"]["tag"] = "tag:stsci.edu/asdf/core/ndarray-1.0.0"
    with pytest.raises(ValidationError, match=r"mismatched tags, wanted .*, got .*"):
        schema.check_schema(s)


def test_fill_and_remove_defaults():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class DefaultType(dict, types.CustomType):
            name = "default"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [DefaultType]

    yaml = """
custom: !<tag:nowhere.org:custom/default-1.0.0>
  b: {}
  d: {}
  g: {}
  j:
    l: 362
    """
    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=[DefaultTypeExtension()]) as ff:
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
    with pytest.warns(AsdfDeprecationWarning, match=r"do_not_fill_defaults"), asdf.open(
        buff,
        extensions=[DefaultTypeExtension()],
        do_not_fill_defaults=True,
    ) as ff:
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

    buff.seek(0)
    with config_context() as config:
        config.legacy_fill_schema_defaults = False
        with asdf.open(buff, extensions=[DefaultTypeExtension()]) as ff:
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

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class OneOfType(dict, types.CustomType):
            name = "one_of"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

    class OneOfTypeExtension(CustomExtension):
        @property
        def types(self):
            return [OneOfType]

    yaml = """
one_of: !<tag:nowhere.org:custom/one_of-1.0.0>
  value: foo
    """
    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=[OneOfTypeExtension()]) as ff:
        assert ff["one_of"]["value"] == "foo"


def test_tag_reference_validation():
    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [TagReferenceType]

    yaml = """
custom: !<tag:nowhere.org:custom/tag_reference-1.0.0>
  name:
    "Something"
  things: !core/ndarray-1.0.0
    data: [1, 2, 3]
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=[DefaultTypeExtension()]) as ff:
        custom = ff.tree["custom"]
        assert custom["name"] == "Something"
        assert_array_equal(custom["things"], [1, 2, 3])


def test_foreign_tag_reference_validation():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class ForeignTagReferenceType(types.CustomType):
            name = "foreign_tag_reference"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

            @classmethod
            def from_tree(cls, tree, ctx):
                node = {}
                node["a"] = tree["a"]
                node["b"] = tree["b"]
                return node

    class ForeignTypeExtension(CustomExtension):
        @property
        def types(self):
            return [TagReferenceType, ForeignTagReferenceType]

    yaml = """
custom: !<tag:nowhere.org:custom/foreign_tag_reference-1.0.0>
  a: !<tag:nowhere.org:custom/tag_reference-1.0.0>
    name:
      "Something"
    things: !core/ndarray-1.0.0
      data: [1, 2, 3]
  b: !<tag:nowhere.org:custom/tag_reference-1.0.0>
    name:
      "Anything"
    things: !core/ndarray-1.0.0
      data: [4, 5, 6]
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=ForeignTypeExtension()) as ff:
        a = ff.tree["custom"]["a"]
        b = ff.tree["custom"]["b"]
        assert a["name"] == "Something"
        assert_array_equal(a["things"], [1, 2, 3])
        assert b["name"] == "Anything"
        assert_array_equal(b["things"], [4, 5, 6])


def test_self_reference_resolution():
    r = resolver.Resolver(CustomExtension().url_mapping, "url")
    s = schema.load_schema(
        helpers.get_test_data_path("self_referencing-1.0.0.yaml"),
        resolver=r,
        resolve_references=True,
    )
    assert "$ref" not in repr(s)
    assert s["anyOf"][1] == s["anyOf"][0]


def test_schema_resolved_via_entry_points():
    """Test that entry points mappings to core schema works"""
    with pytest.warns(AsdfDeprecationWarning, match="get_default_resolver is deprecated"):
        r = extension.get_default_resolver()
    tag = asdf.testing.helpers.format_tag("stsci.edu", "asdf", "1.0.0", "fits/fits")
    with pytest.warns(AsdfDeprecationWarning, match="default_extensions is deprecated"):
        url = extension.default_extensions.extension_list.tag_mapping(tag)

    s = schema.load_schema(url, resolver=r, resolve_references=True)
    assert tag in repr(s)


@pytest.mark.parametrize("num", [constants.MAX_NUMBER + 1, constants.MIN_NUMBER - 1])
def test_max_min_literals(num):
    msg = r"Integer value .* is too large to safely represent as a literal in ASDF"

    tree = {
        "test_int": num,
    }

    with pytest.raises(ValidationError, match=msg):
        asdf.AsdfFile(tree)

    tree = {
        "test_list": [num],
    }

    with pytest.raises(ValidationError, match=msg):
        asdf.AsdfFile(tree)

    tree = {
        num: "test_key",
    }

    with pytest.raises(ValidationError, match=msg):
        asdf.AsdfFile(tree)


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

    buff = helpers.yaml_to_asdf(yaml)

    with pytest.warns(AsdfWarning, match=r"Invalid integer literal value"), asdf.open(buff) as af:
        assert af["integer"] == value

    yaml = f"{value}: foo"

    buff = helpers.yaml_to_asdf(yaml)

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
        with helpers.assert_no_warnings():
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
        with pytest.raises(ValidationError, match=r"Mapping key .* is not permitted"):
            asdf.AsdfFile({key: "value"}, version=version)


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


def test_type_missing_dependencies():
    pytest.importorskip("astropy", "3.0.0")

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class MissingType(types.CustomType):
            name = "missing"
            organization = "nowhere.org"
            version = (1, 1, 0)
            standard = "custom"
            types = ["asdfghjkl12345.foo"]
            requires = ["ASDFGHJKL12345"]

    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [MissingType]

    yaml = """
custom: !<tag:nowhere.org:custom/missing-1.1.0>
  b: {foo: 42}
    """
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(
        AsdfConversionWarning,
        match=r"Failed to convert tag:nowhere.org:custom/missing-1.1.0",
    ), asdf.open(buff, extensions=[DefaultTypeExtension()]) as ff:
        assert ff.tree["custom"]["b"]["foo"] == 42


def test_assert_roundtrip_with_extension(tmp_path):
    called_custom_assert_equal = [False]

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomType(dict, types.CustomType):
            name = "custom_flow"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"

            @classmethod
            def assert_equal(cls, old, new):
                called_custom_assert_equal[0] = True

    class CustomTypeExtension(CustomExtension):
        @property
        def types(self):
            return [CustomType]

    tree = {"custom": CustomType({"a": 42, "b": 43})}

    def check(ff):
        assert isinstance(ff.tree["custom"], CustomType)

    with helpers.assert_no_warnings():
        helpers.assert_roundtrip_tree(tree, tmp_path, extensions=[CustomTypeExtension()])

    assert called_custom_assert_equal[0] is True


def test_custom_validation_bad(tmp_path):
    custom_schema_path = helpers.get_test_data_path("custom_schema.yaml")
    asdf_file = str(tmp_path / "out.asdf")

    # This tree does not conform to the custom schema
    tree = {"stuff": 42, "other_stuff": "hello"}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file using custom schema should fail
    with pytest.raises(ValidationError, match=r".* is a required property"), asdf.AsdfFile(
        tree,
        custom_schema=custom_schema_path,
    ):
        pass

    # Opening file without custom schema should pass
    with asdf.open(asdf_file):
        pass

    # Opening file with custom schema should fail
    with pytest.raises(ValidationError, match=r".* is a required property"), asdf.open(
        asdf_file,
        custom_schema=custom_schema_path,
    ):
        pass


def test_custom_validation_good(tmp_path):
    custom_schema_path = helpers.get_test_data_path("custom_schema.yaml")
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"foo": {"x": 42, "y": 10}, "bar": {"a": "hello", "b": "banjo"}}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_pathlib(tmp_path):
    """
    Make sure custom schema paths can be pathlib.Path objects

    See https://github.com/asdf-format/asdf/issues/653 for discussion.
    """
    from pathlib import Path

    custom_schema_path = Path(helpers.get_test_data_path("custom_schema.yaml"))
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"foo": {"x": 42, "y": 10}, "bar": {"a": "hello", "b": "banjo"}}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_with_definitions_good(tmp_path):
    custom_schema_path = helpers.get_test_data_path("custom_schema_definitions.yaml")
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"thing": {"biz": "hello", "baz": "world"}}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_with_definitions_bad(tmp_path):
    custom_schema_path = helpers.get_test_data_path("custom_schema_definitions.yaml")
    asdf_file = str(tmp_path / "out.asdf")

    # This tree does NOT conform to the custom schema
    tree = {"forb": {"biz": "hello", "baz": "world"}}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file with custom schema should fail
    with pytest.raises(ValidationError, match=r".* is a required property"), asdf.AsdfFile(
        tree,
        custom_schema=custom_schema_path,
    ):
        pass

    # Opening file without custom schema should pass
    with asdf.open(asdf_file):
        pass

    # Opening file with custom schema should fail
    with pytest.raises(ValidationError, match=r".* is a required property"), asdf.open(
        asdf_file,
        custom_schema=custom_schema_path,
    ):
        pass


def test_custom_validation_with_external_ref_good(tmp_path):
    custom_schema_path = helpers.get_test_data_path("custom_schema_external_ref.yaml")
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"foo": asdf.tags.core.Software(name="Microsoft Windows", version="95")}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_with_external_ref_bad(tmp_path):
    custom_schema_path = helpers.get_test_data_path("custom_schema_external_ref.yaml")
    asdf_file = str(tmp_path / "out.asdf")

    # This tree does not conform to the custom schema
    tree = {"foo": False}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file with custom schema should fail
    with pytest.raises(ValidationError, match=r"False is not valid under any of the given schemas"), asdf.AsdfFile(
        tree,
        custom_schema=custom_schema_path,
    ):
        pass

    # Opening file without custom schema should pass
    with asdf.open(asdf_file):
        pass

    # Opening file with custom schema should fail
    with pytest.raises(ValidationError, match=r"False is not valid under any of the given schemas"), asdf.open(
        asdf_file,
        custom_schema=custom_schema_path,
    ):
        pass


def test_load_custom_schema_deprecated():
    custom_schema_path = helpers.get_test_data_path("custom_schema.yaml")

    with pytest.deprecated_call():
        schema.load_custom_schema(custom_schema_path)


def test_load_schema_resolve_local_refs_deprecated():
    custom_schema_path = helpers.get_test_data_path("custom_schema_definitions.yaml")

    with pytest.deprecated_call():
        schema.load_schema(custom_schema_path, resolve_local_refs=True)


def test_nonexistent_tag(tmp_path):
    """
    This tests the case where a node is tagged with a type that apparently
    comes from an extension that is known, but the type itself can't be found.

    This could occur when a more recent version of an installed package
    provides the new type, but an older version of the package is installed.
    ASDF should still be able to open the file in this case, but it won't be
    able to restore the type.

    The bug that prompted this test results from attempting to load a schema
    file that doesn't exist, which is why this test belongs in this file.
    """

    # This shouldn't ever happen, but it's a useful test case
    yaml = """
a: !core/doesnt_exist-1.0.0
  hello
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(AsdfWarning, match=r"Unable to locate schema file"), asdf.open(buff) as af:
        assert str(af["a"]) == "hello"

    # This is a more realistic case since we're using an external extension
    yaml = """
a: !<tag:nowhere.org:custom/doesnt_exist-1.0.0>
  hello
  """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(AsdfWarning, match=r"Unable to locate schema file"), asdf.open(
        buff,
        extensions=CustomExtension(),
    ) as af:
        assert str(af["a"]) == "hello"


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
            msg = "Expected numpy.{} to be {} against jsonschema type '{}'".format(
                type(numpy_value).__name__,
                description,
                jsonschema_type,
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
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.0.0
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
$schema: http://stsci.edu/schemas/asdf/asdf-schema-1.0.0
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
