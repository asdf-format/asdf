import io
from collections import OrderedDict, namedtuple
from typing import NamedTuple

import numpy as np
import pytest
import yaml

import asdf
from asdf import tagged, treeutil, yamlutil
from asdf.exceptions import AsdfWarning

from . import _helpers as helpers


def test_ordered_dict(tmp_path):
    """
    Test that we can write out and read in ordered dicts.
    """

    tree = {
        "ordered_dict": OrderedDict([("first", "foo"), ("second", "bar"), ("third", "baz")]),
        "unordered_dict": {"first": "foo", "second": "bar", "third": "baz"},
    }

    def check_asdf(asdf):
        tree = asdf.tree

        assert isinstance(tree["ordered_dict"], OrderedDict)
        assert list(tree["ordered_dict"].keys()) == ["first", "second", "third"]

        assert not isinstance(tree["unordered_dict"], OrderedDict)
        assert isinstance(tree["unordered_dict"], dict)

    def check_raw_yaml(content):
        assert b"OrderedDict" not in content

    helpers.assert_roundtrip_tree(tree, tmp_path, asdf_check_func=check_asdf, raw_yaml_check_func=check_raw_yaml)


def test_unicode_write(tmp_path):
    """
    We want to write unicode out as regular utf-8-encoded
    characters, not as escape sequences
    """

    tree = {"ɐʇɐp‾ǝpoɔıun": 42, "ascii_only": "this is ascii"}  # noqa: RUF001

    def check_asdf(asdf):
        assert "ɐʇɐp‾ǝpoɔıun" in asdf.tree  # noqa: RUF001
        assert isinstance(asdf.tree["ascii_only"], str)

    def check_raw_yaml(content):
        # Ensure that unicode is written out as UTF-8 without escape
        # sequences
        assert "ɐʇɐp‾ǝpoɔıun".encode() in content  # noqa: RUF001
        # Ensure that the unicode "tag" is not used
        assert b"unicode" not in content

    helpers.assert_roundtrip_tree(tree, tmp_path, asdf_check_func=check_asdf, raw_yaml_check_func=check_raw_yaml)


def test_arbitrary_python_object():
    """
    Putting "just any old" Python object in the tree should raise an
    exception.
    """

    class Foo:
        pass

    tree = {"object": Foo()}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    with pytest.raises(yaml.YAMLError, match=r"\('cannot represent an object', .*\)"):
        ff.write_to(buff)


def run_tuple_test(tree, tmp_path):
    def check_asdf(asdf):
        assert isinstance(asdf.tree["val"], list)

    def check_raw_yaml(content):
        assert b"tuple" not in content

    # Ignore these warnings for the tests that don't actually test the warning
    init_options = {"ignore_implicit_conversion": True}

    helpers.assert_roundtrip_tree(
        tree,
        tmp_path,
        asdf_check_func=check_asdf,
        raw_yaml_check_func=check_raw_yaml,
        init_options=init_options,
    )


def test_python_tuple(tmp_path):
    """
    We don't want to store tuples as tuples, because that's not a
    built-in YAML data type.  This test ensures that they are
    converted to lists.
    """

    tree = {"val": (1, 2, 3)}

    run_tuple_test(tree, tmp_path)


def test_named_tuple_collections(tmp_path):
    """
    Ensure that we are able to serialize a collections.namedtuple.
    """

    nt = namedtuple("TestNamedTuple1", ("one", "two", "three"))

    tree = {"val": nt(1, 2, 3)}

    run_tuple_test(tree, tmp_path)


def test_named_tuple_typing(tmp_path):
    """
    Ensure that we are able to serialize a typing.NamedTuple.
    """

    class NT(NamedTuple):
        one: int
        two: int
        three: int

    tree = {"val": NT(1, 2, 3)}

    run_tuple_test(tree, tmp_path)


def test_named_tuple_collections_recursive(tmp_path):
    nt = namedtuple("TestNamedTuple3", ("one", "two", "three"))

    tree = {"val": nt(1, 2, np.ones(3))}

    def check_asdf(asdf):
        assert (asdf.tree["val"][2] == np.ones(3)).all()

    init_options = {"ignore_implicit_conversion": True}
    helpers.assert_roundtrip_tree(tree, tmp_path, asdf_check_func=check_asdf, init_options=init_options)


def test_named_tuple_typing_recursive(tmp_path):
    class NT(NamedTuple):
        one: int
        two: int
        three: np.ndarray

    tree = {"val": NT(1, 2, np.ones(3))}

    def check_asdf(asdf):
        assert (asdf.tree["val"][2] == np.ones(3)).all()

    init_options = {"ignore_implicit_conversion": True}
    helpers.assert_roundtrip_tree(tree, tmp_path, asdf_check_func=check_asdf, init_options=init_options)


def test_implicit_conversion_warning():
    nt = namedtuple("TestTupleWarning", ("one", "two", "three"))

    tree = {"val": nt(1, 2, np.ones(3))}

    with pytest.warns(AsdfWarning, match=r"Failed to serialize instance"), asdf.AsdfFile(tree):
        pass

    with helpers.assert_no_warnings(), asdf.AsdfFile(tree, ignore_implicit_conversion=True):
        pass


@pytest.mark.xfail(reason="pyyaml has a bug and does not support tuple keys")
def test_python_tuple_key(tmp_path):
    """
    This tests whether tuple keys are round-tripped properly.

    As of this writing, this does not work in pyyaml but does work in
    ruamel.yaml. If/when we decide to switch to ruamel.yaml, this test should
    pass.
    """
    tree = {(42, 1): "foo"}
    helpers.assert_roundtrip_tree(tree, tmp_path)


def test_tags_removed_after_load(tmp_path):
    tree = {"foo": ["bar", (1, 2, None)]}

    def check_asdf(asdf):
        for node in treeutil.iter_tree(asdf.tree):
            if node != asdf.tree:
                assert not isinstance(node, tagged.Tagged)

    helpers.assert_roundtrip_tree(tree, tmp_path, asdf_check_func=check_asdf)


def test_explicit_tags():
    yaml = f"""#ASDF {asdf.versioning.default_version}
%YAML 1.1
--- !<tag:stsci.edu:asdf/core/asdf-1.0.0>
foo: !<tag:stsci.edu:asdf/core/ndarray-1.0.0> [1, 2, 3]
...
    """

    # Check that fully qualified explicit tags work
    buff = helpers.yaml_to_asdf(yaml, yaml_headers=False)

    with asdf.open(buff) as ff:
        assert all(ff.tree["foo"] == [1, 2, 3])


def test_yaml_internal_reference(tmp_path):
    """
    Test that YAML internal references (anchors and aliases) work,
    as well as recursive data structures.
    """

    d = {
        "foo": "2",
    }
    d["bar"] = d

    _list = []
    _list.append(_list)

    tree = {"first": d, "second": d, "list": _list}

    def check_yaml(content):
        assert b"list:&id002-*id002" in b"".join(content.split())

    helpers.assert_roundtrip_tree(tree, tmp_path, raw_yaml_check_func=check_yaml)


def test_yaml_nan_inf():
    tree = {"a": np.nan, "b": np.inf, "c": -np.inf}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    buff.seek(0)
    with asdf.open(buff) as ff:
        assert np.isnan(ff.tree["a"])
        assert np.isinf(ff.tree["b"])
        assert np.isinf(ff.tree["c"])


def test_tag_object():
    class SomeObject:
        pass

    tag = "tag:nowhere.org:none/some/thing"
    instance = tagged.tag_object(tag, SomeObject())
    assert instance._tag == tag


@pytest.mark.parametrize(
    ("numpy_value", "expected_value"),
    [
        (np.str_("foo"), "foo"),
        (np.bytes_("foo"), b"foo"),
        (np.float16(3.14), 3.14),
        (np.float32(3.14159), 3.14159),
        (np.float64(3.14159), 3.14159),
        # Evidently float128 is not available on Windows:
        (getattr(np, "float128", np.float64)(3.14159), 3.14159),
        (np.int8(42), 42),
        (np.int16(42), 42),
        (np.int32(42), 42),
        (np.int64(42), 42),
        (np.longlong(42), 42),
        (np.uint8(42), 42),
        (np.uint16(42), 42),
        (np.uint32(42), 42),
        (np.uint64(42), 42),
        (np.ulonglong(42), 42),
    ],
)
def test_numpy_scalar(numpy_value, expected_value):
    ctx = asdf.AsdfFile({"value": numpy_value})
    tree = ctx.tree
    buffer = io.BytesIO()

    yamlutil.dump_tree(tree, buffer, ctx)
    buffer.seek(0)

    assert yamlutil.load_tree(buffer)["value"] == expected_value
