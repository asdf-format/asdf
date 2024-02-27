import io
from collections import OrderedDict, namedtuple
from typing import NamedTuple

import numpy as np
import pytest
import yaml

import asdf
from asdf import tagged, treeutil, yamlutil
from asdf.exceptions import AsdfConversionWarning, AsdfWarning
from asdf.testing.helpers import yaml_to_asdf


def _roundtrip(obj):
    """
    Parameters
    ----------

    obj : object
        object to write to ASDF file (under key 'obj')

    Returns
    -------

    file_contents: bytes
        contents of written file

    read_tree : object
        object read back from ASDF file
    """
    buff = io.BytesIO()
    asdf.AsdfFile({"obj": obj}).write_to(buff)
    buff.seek(0)

    open_kwargs = {
        "lazy_load": False,
        "copy_arrays": True,
    }

    with asdf.open(buff, **open_kwargs) as af:
        return buff.getvalue(), af["obj"]


def test_ordered_dict():
    """
    Test that we can write out and read in ordered dicts.
    """

    input_tree = {
        "ordered_dict": OrderedDict([("first", "foo"), ("second", "bar"), ("third", "baz")]),
        "unordered_dict": {"first": "foo", "second": "bar", "third": "baz"},
    }

    content, tree = _roundtrip(input_tree)

    assert b"OrderedDict" not in content

    assert isinstance(tree["ordered_dict"], OrderedDict)
    assert tree["ordered_dict"] == input_tree["ordered_dict"]

    assert not isinstance(tree["unordered_dict"], OrderedDict)
    assert isinstance(tree["unordered_dict"], dict)
    assert tree["unordered_dict"] == input_tree["unordered_dict"]


def test_unicode_write():
    """
    We want to write unicode out as regular utf-8-encoded
    characters, not as escape sequences
    """

    input_tree = {"ɐʇɐp‾ǝpoɔıun": 42, "ascii_only": "this is ascii"}  # noqa: RUF001

    content, tree = _roundtrip(input_tree)

    # Ensure that unicode is written out as UTF-8 without escape
    # sequences
    assert "ɐʇɐp‾ǝpoɔıun".encode() in content  # noqa: RUF001
    # Ensure that the unicode "tag" is not used
    assert b"unicode" not in content

    assert tree["ɐʇɐp‾ǝpoɔıun"] == input_tree["ɐʇɐp‾ǝpoɔıun"]  # noqa: RUF001
    assert isinstance(tree["ascii_only"], str)
    assert tree["ascii_only"] == input_tree["ascii_only"]


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


def run_tuple_test(input_tree):
    content, tree = _roundtrip(input_tree)

    assert b"tuple" not in content
    assert isinstance(tree["val"], list)


def test_python_tuple():
    """
    We don't want to store tuples as tuples, because that's not a
    built-in YAML data type.  This test ensures that they are
    converted to lists.
    """

    input_tree = {"val": (1, 2, 3)}

    run_tuple_test(input_tree)


def test_named_tuple_collections():
    """
    Ensure that we are able to serialize a collections.namedtuple.
    """

    nt = namedtuple("TestNamedTuple1", ("one", "two", "three"))

    input_tree = {"val": nt(1, 2, 3)}

    with pytest.warns(AsdfWarning, match="converting to list"):
        run_tuple_test(input_tree)


def test_named_tuple_typing():
    """
    Ensure that we are able to serialize a typing.NamedTuple.
    """

    class NT(NamedTuple):
        one: int
        two: int
        three: int

    tree = {"val": NT(1, 2, 3)}

    with pytest.warns(AsdfWarning, match="converting to list"):
        run_tuple_test(tree)


def test_named_tuple_collections_recursive():
    nt = namedtuple("TestNamedTuple3", ("one", "two", "three"))

    input_tree = {"val": nt(1, 2, np.ones(3))}

    with pytest.warns(AsdfWarning, match="converting to list"):
        _, tree = _roundtrip(input_tree)
    assert (tree["val"][2] == np.ones(3)).all()


def test_named_tuple_typing_recursive(tmp_path):
    class NT(NamedTuple):
        one: int
        two: int
        three: np.ndarray

    input_tree = {"val": NT(1, 2, np.ones(3))}

    with pytest.warns(AsdfWarning, match="converting to list"):
        _, tree = _roundtrip(input_tree)
    assert (tree["val"][2] == np.ones(3)).all()


def test_implicit_conversion_warning():
    nt = namedtuple("TestTupleWarning", ("one", "two", "three"))

    tree = {"val": nt(1, 2, np.ones(3))}

    with pytest.warns(AsdfWarning, match=r"Failed to serialize instance"), asdf.AsdfFile(tree):
        pass

    with asdf.AsdfFile(tree, ignore_implicit_conversion=True):
        pass


@pytest.mark.xfail(reason="pyyaml has a bug and does not support tuple keys")
def test_python_tuple_key():
    """
    This tests whether tuple keys are round-tripped properly.

    As of this writing, this does not work in pyyaml but does work in
    ruamel.yaml. If/when we decide to switch to ruamel.yaml, this test should
    pass.
    """
    input_tree = {(42, 1): "foo"}

    _, tree = _roundtrip(input_tree)
    assert tree[(42, 1)] == "foo"


def test_tags_removed_after_load(tmp_path):
    input_tree = {"foo": ["bar", (1, 2, None)]}

    _, tree = _roundtrip(input_tree)

    for node in treeutil.iter_tree(tree):
        if node != tree:
            assert not isinstance(node, tagged.Tagged)


def test_explicit_tags():
    yaml = b"""#ASDF 1.0.0
#ASDF_STANDARD 1.5.0
%YAML 1.1
--- !<tag:stsci.edu:asdf/core/asdf-1.1.0>
foo: !<tag:stsci.edu:asdf/core/ndarray-1.0.0> [1, 2, 3]
..."""

    # Check that fully qualified explicit tags work
    buff = io.BytesIO(yaml.encode("ascii"))

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

    input_tree = {"first": d, "second": d, "list": _list}

    content, tree = _roundtrip(input_tree)

    assert b"list:&id002-*id002" in b"".join(content.split())
    assert tree["list"][0] == tree["list"]
    for k in ("first", "second"):
        assert tree[k]["foo"] == input_tree[k]["foo"]
        assert tree[k]["bar"] is tree[k]


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

    loaded_value = yamlutil.load_tree(buffer)["value"]
    if isinstance(numpy_value, np.floating):
        abs_diff = abs(expected_value - loaded_value)
        eps = np.finfo(numpy_value.dtype).eps
        assert abs_diff < eps, abs_diff
    else:
        assert loaded_value == expected_value


def test_ndarray_subclass_conversion(tmp_path):
    class MyNDArray(np.ndarray):
        pass

    fn = tmp_path / "test.asdf"
    af = asdf.AsdfFile()
    af["a"] = MyNDArray([1, 2, 3])
    with pytest.warns(AsdfConversionWarning, match=r"A ndarray subclass .*"):
        af.write_to(fn)

    with asdf.config.config_context() as cfg:
        cfg.convert_unknown_ndarray_subclasses = False
        with pytest.raises(yaml.representer.RepresenterError, match=r".*cannot represent.*"):
            af.write_to(fn)


@pytest.mark.parametrize(
    "payload",
    [
        "  1: a",  # not a sequence
        "- !!omap\n  - 1",  # sequence item, not a mapping
        "- !!omap\n  1: a\n  2: a",  # sequence item, not a one element mapping
    ],
)
def test_invalid_omap(payload):
    test_yaml = f"""od: !!omap
{payload}
"""

    # Check that fully qualified explicit tags work
    buff = yaml_to_asdf(test_yaml)

    with pytest.raises(yaml.constructor.ConstructorError):
        with asdf.open(buff) as ff:
            ff["od"]
