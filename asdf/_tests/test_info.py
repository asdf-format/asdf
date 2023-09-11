import os
import pathlib
import re
import tempfile

import numpy as np

import asdf
from asdf.extension import ExtensionManager, ExtensionProxy, ManifestExtension
from asdf.resource import DirectoryResourceMapping


def test_info_module(capsys, tmp_path):
    tree = {
        "foo": 42,
        "bar": "hello",
        "baz": np.arange(20),
        "nested": {"woo": "hoo", "yee": "haw"},
        "long_line": "a" * 100,
    }
    af = asdf.AsdfFile(tree)

    def _assert_correct_info(node_or_path):
        asdf.info(node_or_path)
        captured = capsys.readouterr()
        assert "foo" in captured.out
        assert "bar" in captured.out
        assert "baz" in captured.out

    _assert_correct_info(af)
    _assert_correct_info(af.tree)

    tmpfile = str(tmp_path / "written.asdf")
    af.write_to(tmpfile)
    af.close()

    _assert_correct_info(tmpfile)
    _assert_correct_info(pathlib.Path(tmpfile))

    for i in range(1, 10):
        asdf.info(af, max_rows=i)
        lines = capsys.readouterr().out.strip().split("\n")
        assert len(lines) <= i

    asdf.info(af, max_cols=80)
    assert "(truncated)" in capsys.readouterr().out
    asdf.info(af, max_cols=None)
    captured = capsys.readouterr().out
    assert "(truncated)" not in captured
    assert "a" * 100 in captured

    asdf.info(af, show_values=True)
    assert "hello" in capsys.readouterr().out
    asdf.info(af, show_values=False)
    assert "hello" not in capsys.readouterr().out

    tree = {"foo": ["alpha", "bravo", "charlie", "delta", "eagle"]}
    af = asdf.AsdfFile(tree)
    asdf.info(af, max_rows=(None,))
    assert "alpha" not in capsys.readouterr().out
    for i in range(1, 5):
        asdf.info(af, max_rows=(None, i))
        captured = capsys.readouterr()
        for val in tree["foo"][0 : i - 1]:
            assert val in captured.out
        for val in tree["foo"][i - 1 :]:
            assert val not in captured.out


class ObjectWithInfoSupport:
    def __init__(self, clown="", the_meaning=0, anyof=None, allof=None, oneof=None, **kw):
        self._tag = "asdf://somewhere.org/asdf/tags/foo-1.0.0"
        self.clown = clown
        self.the_meaning_of_life_the_universe_and_everything = the_meaning
        self.anyof = anyof
        self.allof = allof
        self.oneof = oneof
        self.patt = {}
        for key in kw:
            if re.search("^S_", key):
                if not isinstance(kw[key], str):
                    msg = "S_ pattern object must be a string"
                    raise ValueError(msg)
                self.patt[key] = kw[key]
            if re.search("^I_", key):
                if not isinstance(kw[key], int):
                    msg = "I_ pattern object must be an int"
                    raise ValueError(msg)
                self.patt[key] = kw[key]

    def __asdf_traverse__(self):
        returnval = {
            "the_meaning_of_life_the_universe_and_everything": self.the_meaning_of_life_the_universe_and_everything,
            "clown": self.clown,
        }
        if self.anyof is not None:
            returnval["anyof_attribute"] = self.anyof
        if self.allof is not None:
            returnval["allof_attribute"] = self.allof
        if self.oneof is not None:
            returnval["oneof_attribute"] = self.oneof
        for key in self.patt:
            returnval[key] = self.patt[key]
        return returnval


class ObjectWithInfoSupport2:
    def __init__(self, attribute1="", attribute2=""):
        self._tag = "asdf://somewhere.org/asdf/tags/bar-1.0.0"
        self.attribute1 = attribute1
        self.attribute2 = attribute2

    def __asdf_traverse__(self):
        return {
            "attribute1": self.attribute1,
            "attribute2": self.attribute2,
        }


class ObjectWithInfoSupport3:
    def __init__(self, attribute_one="", attribute_two=""):
        self._tag = "asdf://somewhere.org/asdf/tags/drink-1.0.0"
        self.attribute_one = attribute_one
        self.attribute_two = attribute_two

    def __asdf_traverse__(self):
        return {
            "attributeOne": self.attribute_one,
            "attributeTwo": self.attribute_two,
        }


def manifest_extension(tmp_path):
    foo_manifest = """%YAML 1.1
---
id: asdf://somewhere.org/asdf/manifests/foo_manifest-1.0
extension_uri: asdf://somewhere.org/asdf/extensions/foo_manifest-1.0
asdf_standard_requirement:
  gte: 1.6.0
  lt: 2.0.0
tags:
  - tag_uri: asdf://somewhere.org/asdf/tags/foo-1.0.0
    schema_uri: asdf://somewhere.org/asdf/schemas/foo-1.0.0
    title: Foo title
    description: Foo description
  - tag_uri: asdf://somewhere.org/asdf/tags/bar-1.0.0
    schema_uri: asdf://somewhere.org/asdf/schemas/bar-1.0.0
    title: Bar title
    description: Bar Description
  - tag_uri: asdf://somewhere.org/asdf/tags/drink-1.0.0
    schema_uri: asdf://somewhere.org/asdf/schemas/drink-1.0.0
    title: Drink title
    description: Drink Description
...
"""
    foo_schema = """
%YAML 1.1
---
$schema: "asdf://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "asdf://somewhere.org/asdf/schemas/foo-1.0.0"

type: object
title: object with info support title
description: object with info support description
properties:
  the_meaning_of_life_the_universe_and_everything:
    title: Some silly title
    description: Some silly description
    type: integer
    archive_catalog:
        datatype: int
        destination: [ScienceCommon.silly]
  clown:
    title: clown name
    description: clown description
    type: string
    archive_catalog:
        datatype: str
        destination: [ScienceCommon.clown]
  anyof_attribute:
    title: anyOf example attribute
    description: anyOf description
    anyOf:
      - type: string
      - type: number
      - type: object
        properties:
          value:
            title: nested object in anyof example
            description: nested object description
            type: integer
          comment:
            title: comment for property
            description: comment description
            type: string
      - tag: asdf://somewhere.org/tags/bar-1.0.0
  oneof_attribute:
    title: oneOf example attribute
    description: oneOf description
    oneOf:
      - type: integer
        multipleOf: 5
      - type: integer
        multipleOf: 3
  allof_attribute:
    title: allOf example attribute
    description: allOf description
    allOf:
      - type: string
      - maxLength: 5
  patternProperties:
    "^S_":
      title: string pattern property
      type: string
    "^I_":
      title: integer pattern property
      type: integer
...
"""

    bar_schema = """
%YAML 1.1
---
$schema: "asdf://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "asdf://somewhere.org/asdf/schemas/bar-1.0.0"

type: object
title: object with info support 2 title
properties:
  attribute1:
    title: Attribute1 Title
    type: string
    archive_catalog:
        datatype: str
        destination: [ScienceCommon.attribute1]
  attribute2:
    title: Attribute2 Title
    type: string
    archive_catalog:
        datatype: str
        destination: [ScienceCommon.attribute2]
...
"""

    drink_schema = """
%YAML 1.1
---
$schema: "asdf://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "asdf://somewhere.org/asdf/schemas/drink-1.0.0"

type: object
title: object with info support 3 title
description: object description
properties:
  attributeOne:
    title: AttributeOne Title
    description: AttributeOne description
    type: string
    archive_catalog:
        datatype: str
        destination: [ScienceCommon.attributeOne]
  attributeTwo:
    title: AttributeTwo Title
    description: AttributeTwo description
    type: string
    archive_catalog:
        datatype: str
        destination: [ScienceCommon.attributeTwo]
...
"""
    os.mkdir(tmp_path / "schemas")
    spath = tmp_path / "schemas" / "foo-1.0.0.yaml"
    with open(spath, "w") as fschema:
        fschema.write(foo_schema)
    spath = tmp_path / "schemas" / "bar-1.0.0.yaml"
    with open(spath, "w") as fschema:
        fschema.write(bar_schema)
    spath = tmp_path / "schemas" / "drink-1.0.0.yaml"
    with open(spath, "w") as fschema:
        fschema.write(drink_schema)
    os.mkdir(tmp_path / "manifests")
    mpath = str(tmp_path / "manifests" / "foo_manifest-1.0.yaml")
    with open(mpath, "w") as fmanifest:
        fmanifest.write(foo_manifest)
    config = asdf.get_config()
    config.add_resource_mapping(
        DirectoryResourceMapping(str(tmp_path / "manifests"), "asdf://somewhere.org/asdf/manifests/"),
    )
    config.add_resource_mapping(
        DirectoryResourceMapping(str(tmp_path / "schemas"), "asdf://somewhere.org/asdf/schemas/"),
    )

    class FooConverter:
        tags = ["asdf://somewhere.org/asdf/tags/foo-1.0.0"]
        types = [ObjectWithInfoSupport]

        def to_yaml_tree(self, obj, tag, ctx):
            node = {
                "the_meaning_of_life_the_universe_and_everything": obj.the_meaning_of_life_the_universe_and_everything,
                "clown": obj.clown,
            }
            if obj.anyof is not None:
                node["anyof_attribute"] = obj.anyof
            if obj.oneof is not None:
                node["oneof_attribute"] = obj.oneof
            if obj.allof is not None:
                node["allof_attribute"] = obj.allof
            return node

        def from_yaml_tree(self, node, tag, ctx):
            return ObjectWithInfoSupport(
                the_meaning=node["the_meaning_of_life_the_universe_and_everything"],
                clown=node["clown"],
            )

    class BarConverter:
        tags = ["asdf://somewhere.org/asdf/tags/bar-1.0.0"]
        types = [ObjectWithInfoSupport2]

        def to_yaml_tree(self, obj, tag, ctx):
            return {
                "attribute1": obj.attribute1,
                "attribute2": obj.attribute2,
            }

        def from_yaml_tree(self, node, tag, ctx):
            return ObjectWithInfoSupport(attribute1="value1", attribute2="value2")

    class DrinkConverter:
        tags = ["asdf://somewhere.org/asdf/tags/drink-1.0.0"]
        types = [ObjectWithInfoSupport3]

        def to_yaml_tree(self, obj, tag, ctx):
            return {
                "attributeOne": obj.attribute_one,
                "attributeTwo": obj.attribute_two,
            }

        def from_yaml_tree(self, node, tag, ctx):
            return ObjectWithInfoSupport(attribute_one="value1", attribute_two="value2")

    converter1 = FooConverter()
    converter2 = BarConverter()
    converter3 = DrinkConverter()

    extension = ManifestExtension.from_uri(
        "asdf://somewhere.org/asdf/manifests/foo_manifest-1.0",
        converters=[converter1, converter2, converter3],
    )
    config = asdf.get_config()
    proxy = ExtensionProxy(extension)
    config.add_extension(proxy)


def create_tree():
    return {
        "random": 3.14159,
        "object": ObjectWithInfoSupport(
            "Bozo",
            42,
            anyof=ObjectWithInfoSupport2("VAL1", "VAL2"),
            oneof=20,
            allof="good",
            S_example="beep",
            I_example=1,
        ),
        "list_of_stuff": [
            ObjectWithInfoSupport3("v1", "v2"),
            ObjectWithInfoSupport3("x1", "x2"),
        ],
    }


def test_schema_info_support(tmp_path):
    manifest_extension(tmp_path)
    config = asdf.get_config()
    af = asdf.AsdfFile()
    af._extension_manager = ExtensionManager(config.extensions)
    af.tree = create_tree()

    assert af.schema_info("title", refresh_extension_manager=True) == {
        "list_of_stuff": [
            {
                "attributeOne": {
                    "title": ("AttributeOne Title", "v1"),
                },
                "attributeTwo": {
                    "title": ("AttributeTwo Title", "v2"),
                },
                "title": ("object with info support 3 title", af.tree["list_of_stuff"][0]),
            },
            {
                "attributeOne": {
                    "title": ("AttributeOne Title", "x1"),
                },
                "attributeTwo": {
                    "title": ("AttributeTwo Title", "x2"),
                },
                "title": ("object with info support 3 title", af.tree["list_of_stuff"][1]),
            },
        ],
        "object": {
            "I_example": {"title": ("integer pattern property", 1)},
            "S_example": {"title": ("string pattern property", "beep")},
            "allof_attribute": {"title": ("allOf example attribute", "good")},
            "anyof_attribute": {
                "attribute1": {
                    "title": ("Attribute1 Title", "VAL1"),
                },
                "attribute2": {
                    "title": ("Attribute2 Title", "VAL2"),
                },
                "title": ("object with info support 2 title", af.tree["object"].anyof),
            },
            "clown": {"title": ("clown name", "Bozo")},
            "oneof_attribute": {"title": ("oneOf example attribute", 20)},
            "the_meaning_of_life_the_universe_and_everything": {"title": ("Some silly title", 42)},
            "title": ("object with info support title", af.tree["object"]),
        },
    }

    assert af.schema_info("archive_catalog", refresh_extension_manager=True) == {
        "list_of_stuff": [
            {
                "attributeOne": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeOne"]}, "v1"),
                },
                "attributeTwo": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeTwo"]}, "v2"),
                },
            },
            {
                "attributeOne": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeOne"]}, "x1"),
                },
                "attributeTwo": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeTwo"]}, "x2"),
                },
            },
        ],
        "object": {
            "anyof_attribute": {
                "attribute1": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attribute1"]}, "VAL1"),
                },
                "attribute2": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attribute2"]}, "VAL2"),
                },
            },
            "clown": {
                "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.clown"]}, "Bozo"),
            },
            "the_meaning_of_life_the_universe_and_everything": {
                "archive_catalog": ({"datatype": "int", "destination": ["ScienceCommon.silly"]}, 42),
            },
        },
    }

    assert af.schema_info("archive_catalog", preserve_list=False, refresh_extension_manager=True) == {
        "list_of_stuff": {
            0: {
                "attributeOne": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeOne"]}, "v1"),
                },
                "attributeTwo": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeTwo"]}, "v2"),
                },
            },
            1: {
                "attributeOne": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeOne"]}, "x1"),
                },
                "attributeTwo": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attributeTwo"]}, "x2"),
                },
            },
        },
        "object": {
            "anyof_attribute": {
                "attribute1": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attribute1"]}, "VAL1"),
                },
                "attribute2": {
                    "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.attribute2"]}, "VAL2"),
                },
            },
            "clown": {
                "archive_catalog": ({"datatype": "str", "destination": ["ScienceCommon.clown"]}, "Bozo"),
            },
            "the_meaning_of_life_the_universe_and_everything": {
                "archive_catalog": ({"datatype": "int", "destination": ["ScienceCommon.silly"]}, 42),
            },
        },
    }

    assert af.schema_info("title", "list_of_stuff", refresh_extension_manager=True) == [
        {
            "attributeOne": {
                "title": ("AttributeOne Title", "v1"),
            },
            "attributeTwo": {
                "title": ("AttributeTwo Title", "v2"),
            },
            "title": ("object with info support 3 title", af.tree["list_of_stuff"][0]),
        },
        {
            "attributeOne": {
                "title": ("AttributeOne Title", "x1"),
            },
            "attributeTwo": {
                "title": ("AttributeTwo Title", "x2"),
            },
            "title": ("object with info support 3 title", af.tree["list_of_stuff"][1]),
        },
    ]

    assert af.schema_info("title", "object", refresh_extension_manager=True) == {
        "I_example": {"title": ("integer pattern property", 1)},
        "S_example": {"title": ("string pattern property", "beep")},
        "allof_attribute": {"title": ("allOf example attribute", "good")},
        "anyof_attribute": {
            "attribute1": {
                "title": ("Attribute1 Title", "VAL1"),
            },
            "attribute2": {
                "title": ("Attribute2 Title", "VAL2"),
            },
            "title": ("object with info support 2 title", af.tree["object"].anyof),
        },
        "clown": {"title": ("clown name", "Bozo")},
        "oneof_attribute": {"title": ("oneOf example attribute", 20)},
        "the_meaning_of_life_the_universe_and_everything": {"title": ("Some silly title", 42)},
        "title": ("object with info support title", af.tree["object"]),
    }

    assert af.schema_info("title", "object.anyof_attribute", refresh_extension_manager=True) == {
        "attribute1": {
            "title": ("Attribute1 Title", "VAL1"),
        },
        "attribute2": {
            "title": ("Attribute2 Title", "VAL2"),
        },
        "title": ("object with info support 2 title", af.tree["object"].anyof),
    }

    assert af.schema_info("title", "object.anyof_attribute.attribute2", refresh_extension_manager=True) == {
        "title": ("Attribute2 Title", "VAL2"),
    }

    # Test printing the schema_info
    assert (
        af.schema_info("title", "object.anyof_attribute.attribute2", refresh_extension_manager=True).__repr__()
        == "{'title': Attribute2 Title}"
    )

    assert af.schema_info("title", "object.anyof_attribute.attribute2.foo", refresh_extension_manager=True) is None

    assert af.schema_info(refresh_extension_manager=True) == {
        "list_of_stuff": [
            {
                "attributeOne": {"description": ("AttributeOne description", "v1")},
                "attributeTwo": {"description": ("AttributeTwo description", "v2")},
                "description": ("object description", af.tree["list_of_stuff"][0]),
            },
            {
                "attributeOne": {"description": ("AttributeOne description", "x1")},
                "attributeTwo": {"description": ("AttributeTwo description", "x2")},
                "description": ("object description", af.tree["list_of_stuff"][1]),
            },
        ],
        "object": {
            "allof_attribute": {
                "description": ("allOf description", "good"),
            },
            "clown": {
                "description": ("clown description", "Bozo"),
            },
            "description": ("object with info support description", af.tree["object"]),
            "oneof_attribute": {
                "description": ("oneOf description", 20),
            },
            "the_meaning_of_life_the_universe_and_everything": {
                "description": ("Some silly description", 42),
            },
        },
    }

    # Test using a search result
    search = af.search("clown")
    assert af.schema_info("description", search, refresh_extension_manager=True) == {
        "object": {
            "clown": {
                "description": ("clown description", "Bozo"),
            },
            "description": ("object with info support description", af.tree["object"]),
        },
    }


def test_info_object_support(capsys, tmp_path):
    manifest_extension(tmp_path)
    config = asdf.get_config()
    af = asdf.AsdfFile()
    af._extension_manager = ExtensionManager(config.extensions)
    af.tree = create_tree()
    af.info(refresh_extension_manager=True)

    captured = capsys.readouterr()

    assert "the_meaning_of_life_the_universe_and_everything" in captured.out
    assert "clown" in captured.out
    assert "42" in captured.out
    assert "Bozo" in captured.out
    assert "clown name" in captured.out
    assert "silly" in captured.out
    assert "info support 2" in captured.out
    assert "Attribute2 Title" in captured.out
    assert "allOf example attribute" in captured.out
    assert "oneOf example attribute" in captured.out
    assert "string pattern property" in captured.out
    assert "integer pattern property" in captured.out
    assert "AttributeOne" in captured.out
    assert "AttributeTwo" in captured.out


class RecursiveObjectWithInfoSupport:
    def __init__(self):
        self._tag = "asdf://somewhere.org/asdf/tags/bar-1.0.0"
        self.the_meaning = 42
        self.clown = "Bozo"
        self.recursive = None

    def __asdf_traverse__(self):
        return {"the_meaning": self.the_meaning, "clown": self.clown, "recursive": self.recursive}


def test_recursive_info_object_support(capsys, tmp_path):
    tempdir = pathlib.Path(tempfile.mkdtemp())
    manifest_extension(tempdir)
    config = asdf.get_config()
    af = asdf.AsdfFile()
    af._extension_manager = ExtensionManager(config.extensions)

    recursive_obj = RecursiveObjectWithInfoSupport()
    recursive_obj.recursive = recursive_obj
    tree = {"random": 3.14159, "rtest": recursive_obj}
    af = asdf.AsdfFile(tree)
    af.info(refresh_extension_manager=True)
    captured = capsys.readouterr()
    assert "recursive reference" in captured.out


def test_search():
    tree = {"foo": 42, "bar": "hello", "baz": np.arange(20)}
    af = asdf.AsdfFile(tree)

    result = af.search("foo")
    assert result.node == 42

    result = af.search(type_="ndarray")
    assert (result.node == tree["baz"]).all()

    result = af.search(value="hello")
    assert result.node == "hello"
