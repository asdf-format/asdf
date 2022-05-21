import os
import pathlib
import re
import shutil
import tempfile

import numpy as np

import asdf
from asdf.extension import ExtensionManager, ExtensionProxy, ManifestExtension
from asdf.resource import DirectoryResourceMapping


def test_info_module(capsys, tmpdir):
    tree = dict(foo=42, bar="hello", baz=np.arange(20), nested={"woo": "hoo", "yee": "haw"}, long_line="a" * 100)
    af = asdf.AsdfFile(tree)

    def _assert_correct_info(node_or_path):
        asdf.info(node_or_path)
        captured = capsys.readouterr()
        assert "foo" in captured.out
        assert "bar" in captured.out
        assert "baz" in captured.out

    _assert_correct_info(af)
    _assert_correct_info(af.tree)

    tmpfile = str(tmpdir.join("written.asdf"))
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


# def test_info_asdf_file(capsys, tmpdir):
#     tree = dict(
#         foo=42, bar="hello", baz=np.arange(20),
#         nested={"woo": "hoo", "yee": "haw"},
#         long_line="a" * 100
#     )
#     af = asdf.AsdfFile(tree)
#     af.info()
#     captured = capsys.readouterr()
#     assert "foo" in captured.out
#     assert "bar" in captured.out
#     assert "baz" in captured.out


class ObjectWithInfoSupport:
    def __init__(self, clown="", the_meaning=0, anyof=None, allof=None, oneof=None, **kw):
        self._tag = "asdf://somewhere.org/asdf/tags/foo-1.0.0"
        self.clown = clown
        self.the_meaning_of_life_the_universe_and_everything = the_meaning
        self.anyof = anyof
        self.allof = allof
        self.oneof = oneof
        self.patt = {}
        for key in kw.keys():
            if re.search("^S_", key):
                if type(kw[key]) != str:
                    raise ValueError("S_ pattern object must be a string")
                self.patt[key] = kw[key]
            if re.search("^I_", key):
                if type(kw[key]) != int:
                    raise ValueError("I_ pattern object must be an int")
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
        returnval = {"attribute1": self.attribute1, "attribute2": self.attribute2}
        return returnval


class ObjectWithInfoSupport3:
    def __init__(self, attribute_one="", attribute_two=""):
        self._tag = "asdf://somewhere.org/asdf/tags/drink-1.0.0"
        self.attribute_one = attribute_one
        self.attribute_two = attribute_two

    def __asdf_traverse__(self):
        returnval = {"attributeOne": self.attribute_one, "attributeTwo": self.attribute_two}
        return returnval


def manifest_extension(tmpdir):

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
properties:
  the_meaning_of_life_the_universe_and_everything:
    title: Some silly title
    type: integer
  clown:
    title: clown name
    type: string
  anyof_attribute:
    title: anyOf example attribute
    anyOf:
      - type: string
      - type: number
      - type: object
        properties:
          value:
            title: nested object in anyof example
            type: integer
          comment:
            title: comment for property
            type: string
      - tag: asdf://somewhere.org/tags/bar-1.0.0
  oneof_attribute:
    title: oneOf example attribute
    oneOf:
      - type: integer
        multipleOf: 5
      - type: integer
        multipleOf: 3
  allof_attribute:
    title: allOf example attribute
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
  attribute2:
    title: Attribute2 Title
    type: string
...
"""

    drink_schema = """
%YAML 1.1
---
$schema: "asdf://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "asdf://somewhere.org/asdf/schemas/drink-1.0.0"

type: object
title: object with info support 3 title
properties:
  attributeOne:
    title: AttributeOne Title
    type: string
  attributeTwo:
    title: AttributeTwo Title
    type: string
...
"""
    os.mkdir(tmpdir / "schemas")
    spath = tmpdir / "schemas" / "foo-1.0.0.yaml"
    with open(spath, "w") as fschema:
        fschema.write(foo_schema)
    spath = tmpdir / "schemas" / "bar-1.0.0.yaml"
    with open(spath, "w") as fschema:
        fschema.write(bar_schema)
    spath = tmpdir / "schemas" / "drink-1.0.0.yaml"
    with open(spath, "w") as fschema:
        fschema.write(drink_schema)
    os.mkdir(tmpdir / "manifests")
    mpath = str(tmpdir / "manifests" / "foo_manifest-1.0.yaml")
    with open(mpath, "w") as fmanifest:
        fmanifest.write(foo_manifest)
    config = asdf.get_config()
    config.add_resource_mapping(
        DirectoryResourceMapping(str(tmpdir / "manifests"), "asdf://somewhere.org/asdf/manifests/")
    )
    config.add_resource_mapping(DirectoryResourceMapping(str(tmpdir / "schemas"), "asdf://somewhere.org/asdf/schemas/"))

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
                the_meaning=node["the_meaning_of_life_the_universe_and_everything"], clown=node["clown"]
            )

    class BarConverter:
        tags = ["asdf://somewhere.org/asdf/tags/bar-1.0.0"]
        types = [ObjectWithInfoSupport2]

        def to_yaml_tree(self, obj, tag, ctx):
            node = {"attribute1": obj.attribute1, "attribute2": obj.attribute2}
            return node

        def from_yaml_tree(self, node, tag, ctx):
            return ObjectWithInfoSupport(attribute1="value1", attribute2="value2")

    class DrinkConverter:
        tags = ["asdf://somewhere.org/asdf/tags/drink-1.0.0"]
        types = [ObjectWithInfoSupport3]

        def to_yaml_tree(self, obj, tag, ctx):
            node = {"attributeOne": obj.attribute_one, "attributeTwo": obj.attribute_two}
            return node

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


def test_info_object_support(capsys):

    tempdir = pathlib.Path(tempfile.mkdtemp())
    manifest_extension(tempdir)
    config = asdf.get_config()
    af = asdf.AsdfFile()
    af._extension_manager = ExtensionManager(config.extensions)
    af.tree = {
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

    shutil.rmtree(tempdir)


class RecursiveObjectWithInfoSupport:
    def __init__(self):
        self._tag = "asdf://somewhere.org/asdf/tags/bar-1.0.0"
        self.the_meaning = 42
        self.clown = "Bozo"
        self.recursive = None

    def __asdf_traverse__(self):
        return {"the_meaning": self.the_meaning, "clown": self.clown, "recursive": self.recursive}


def test_recursive_info_object_support(capsys, tmpdir):
    tempdir = pathlib.Path(tempfile.mkdtemp())
    manifest_extension(tempdir)
    config = asdf.get_config()
    af = asdf.AsdfFile()
    af._extension_manager = ExtensionManager(config.extensions)

    recursive_obj = RecursiveObjectWithInfoSupport()
    recursive_obj.recursive = recursive_obj
    tree = dict(random=3.14159, rtest=recursive_obj)
    af = asdf.AsdfFile(tree)
    af.info(refresh_extension_manager=True)
    captured = capsys.readouterr()
    assert "recursive reference" in captured.out


def test_search():
    tree = dict(foo=42, bar="hello", baz=np.arange(20))
    af = asdf.AsdfFile(tree)

    result = af.search("foo")
    assert result.node == 42

    result = af.search(type="ndarray")
    assert (result.node == tree["baz"]).all()

    result = af.search(value="hello")
    assert result.node == "hello"
