import collections
import copy
import json
import weakref

import numpy as np
import pytest

import asdf
from asdf import _lazy_nodes


def test_slice_access():
    af = asdf.AsdfFile()
    node = _lazy_nodes.AsdfListNode([0, 1, 2], weakref.ref(af))
    assert node[0] == 0
    assert node[1] == 1
    assert node[2] == 2
    assert node[:2] == [0, 1]
    assert isinstance(node[:2], _lazy_nodes.AsdfListNode)
    assert node[1:2] == [
        1,
    ]
    assert isinstance(node[1:2], _lazy_nodes.AsdfListNode)
    assert node[:-1] == [0, 1]
    assert isinstance(node[:-1], _lazy_nodes.AsdfListNode)
    assert node[::-1] == [2, 1, 0]
    assert isinstance(node[::-1], _lazy_nodes.AsdfListNode)
    assert node[::2] == [0, 2]
    assert isinstance(node[::2], _lazy_nodes.AsdfListNode)
    assert node[1::2] == [
        1,
    ]
    assert isinstance(node[1::2], _lazy_nodes.AsdfListNode)


def test_nested_node_conversion():
    tree = {
        # lll = list in list in list, etc...
        "lll": [[[0]]],
        "lld": [[{"a": 0}]],
        "ldl": [{"a": [0]}],
        "ldd": [{"a": {"a": [0]}}],
        "dll": {"a": [[0]]},
        "dld": {"a": [{"a": 0}]},
        "ddl": {"a": {"a": [0]}},
        "ddd": {"a": {"a": {"a": 0}}},
    }
    af = asdf.AsdfFile()
    node = _lazy_nodes.AsdfDictNode(tree, weakref.ref(af))
    for key in node:
        obj = node[key]
        for code in key:
            if code == "l":
                assert isinstance(obj, _lazy_nodes.AsdfListNode)
                obj = obj[0]
            else:
                assert isinstance(obj, _lazy_nodes.AsdfDictNode)
                obj = obj["a"]


def test_lazy_tree_ref(tmp_path):
    fn = tmp_path / "test.asdf"

    arr = np.arange(42)
    tree = {
        "a": arr,
        "b": {"c": arr},
        "d": [
            arr,
        ],
    }

    af = asdf.AsdfFile(tree)
    af.write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        assert isinstance(af.tree.data.data["a"], asdf.tagged.Tagged)
        assert isinstance(af.tree.data.data["b"]["c"], asdf.tagged.Tagged)
        assert isinstance(af.tree.data.data["d"][0], asdf.tagged.Tagged)
        assert isinstance(af["b"], _lazy_nodes.AsdfDictNode)
        assert isinstance(af["d"], _lazy_nodes.AsdfListNode)
        np.testing.assert_array_equal(af["a"], arr)
        assert af["a"] is af["b"]["c"]
        assert af["a"] is af["d"][0]


def test_ordered_dict():
    tree = {"a": collections.OrderedDict({"b": [1, 2, collections.OrderedDict({"c": 3})]})}

    af = asdf.AsdfFile()

    node = _lazy_nodes.AsdfDictNode(tree, weakref.ref(af))
    assert isinstance(node["a"], _lazy_nodes.AsdfOrderedDictNode)
    assert isinstance(node["a"]["b"], _lazy_nodes.AsdfListNode)
    assert isinstance(node["a"]["b"][2], _lazy_nodes.AsdfOrderedDictNode)


@pytest.mark.parametrize(
    "node",
    [
        _lazy_nodes.AsdfDictNode({"a": 1, "b": 2}),
        _lazy_nodes.AsdfListNode([1, 2, 3]),
        _lazy_nodes.AsdfOrderedDictNode({"a": 1, "b": 2}),
    ],
)
@pytest.mark.parametrize("copy_operation", [copy.copy, copy.deepcopy])
def test_copy(node, copy_operation):
    copied_node = copy_operation(node)
    assert isinstance(copied_node, type(node))
    assert copied_node == node


@pytest.mark.parametrize(
    "node",
    [
        _lazy_nodes.AsdfDictNode({"a": 1, "b": 2}),
        _lazy_nodes.AsdfListNode([1, 2, 3]),
        _lazy_nodes.AsdfOrderedDictNode({"a": 1, "b": 2}),
    ],
)
def test_json_serialization(node):
    rt_node = json.loads(json.dumps(node))
    assert rt_node == node


def test_cache_clear_on_close(tmp_path):
    fn = tmp_path / "test.asdf"

    arr = np.arange(42)
    tree = {"a": arr}
    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        # grab a weakref to this array, it should fail
        # to resolve after the with exits
        ref = weakref.ref(af["a"])

    assert ref() is None


def test_access_after_del(tmp_path):
    fn = tmp_path / "test.asdf"

    arr = np.arange(42)
    tree = {"a": {"b": arr}}
    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        d = af["a"]

    del af

    with pytest.raises(Exception, match="no ASDF for you!"):
        d["b"]
