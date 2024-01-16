import collections
import copy
import json
import weakref

import numpy as np
import pytest

import asdf
from asdf.lazy_nodes import AsdfDictNode, AsdfListNode, AsdfOrderedDictNode, _resolve_af_ref, _to_lazy_node


def test_slice_access():
    af = asdf.AsdfFile()
    node = AsdfListNode([0, 1, 2], weakref.ref(af))
    assert node[0] == 0
    assert node[1] == 1
    assert node[2] == 2
    assert node[:2] == [0, 1]
    assert isinstance(node[:2], AsdfListNode)
    assert node[1:2] == [
        1,
    ]
    assert isinstance(node[1:2], AsdfListNode)
    assert node[:-1] == [0, 1]
    assert isinstance(node[:-1], AsdfListNode)
    assert node[::-1] == [2, 1, 0]
    assert isinstance(node[::-1], AsdfListNode)
    assert node[::2] == [0, 2]
    assert isinstance(node[::2], AsdfListNode)
    assert node[1::2] == [
        1,
    ]
    assert isinstance(node[1::2], AsdfListNode)


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
    node = AsdfDictNode(tree, weakref.ref(af))
    for key in node:
        obj = node[key]
        for code in key:
            if code == "l":
                assert isinstance(obj, AsdfListNode)
                obj = obj[0]
            else:
                assert isinstance(obj, AsdfDictNode)
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
        assert isinstance(af.tree.data.tagged["a"], asdf.tagged.Tagged)
        assert isinstance(af.tree.data.tagged["b"]["c"], asdf.tagged.Tagged)
        assert isinstance(af.tree.data.tagged["d"][0], asdf.tagged.Tagged)
        assert isinstance(af["b"], AsdfDictNode)
        assert isinstance(af["d"], AsdfListNode)
        np.testing.assert_array_equal(af["a"], arr)
        assert af["a"] is af["b"]["c"]
        assert af["a"] is af["d"][0]


def test_ordered_dict():
    tree = {"a": collections.OrderedDict({"b": [1, 2, collections.OrderedDict({"c": 3})]})}

    af = asdf.AsdfFile()

    node = AsdfDictNode(tree, weakref.ref(af))
    assert isinstance(node["a"], AsdfOrderedDictNode)
    assert isinstance(node["a"]["b"], AsdfListNode)
    assert isinstance(node["a"]["b"][2], AsdfOrderedDictNode)


@pytest.mark.parametrize(
    "NodeClass,data,base",
    [
        (AsdfDictNode, {"a": 1}, dict),
        (AsdfListNode, [1, 2], list),
        (AsdfOrderedDictNode, {"a": 1}, collections.OrderedDict),
    ],
)
def test_node_inheritance(NodeClass, data, base):
    node = NodeClass(data)
    assert isinstance(node, base)


@pytest.mark.parametrize(
    "NodeClass,base",
    [
        (AsdfDictNode, dict),
        (AsdfListNode, list),
        (AsdfOrderedDictNode, dict),
    ],
)
def test_node_empty_init(NodeClass, base):
    node = NodeClass()
    assert type(node.tagged) == base


@pytest.mark.parametrize(
    "node",
    [
        AsdfDictNode({"a": 1, "b": 2}),
        AsdfListNode([1, 2, 3]),
        AsdfOrderedDictNode({"a": 1, "b": 2}),
    ],
)
@pytest.mark.parametrize("copy_operation", [copy.copy, copy.deepcopy])
def test_copy(node, copy_operation):
    copied_node = copy_operation(node)
    assert isinstance(copied_node, type(node))
    assert copied_node == node


@pytest.mark.parametrize(
    "NodeClass,data",
    [
        (AsdfDictNode, {1: "a", 2: "b"}),
        (AsdfListNode, [1, 2]),
        (AsdfOrderedDictNode, collections.OrderedDict({1: "a", 2: "b"})),
    ],
)
def test_node_equality(NodeClass, data):
    node = NodeClass(data)
    assert node == node
    assert not node != node
    assert node == data
    data.pop(1)
    assert node != data


@pytest.mark.parametrize(
    "node",
    [
        AsdfDictNode({"a": 1, "b": 2}),
        AsdfListNode([1, 2, 3]),
        AsdfOrderedDictNode({"a": 1, "b": 2}),
    ],
)
def test_json_serialization(node):
    with pytest.raises(TypeError, match="is not JSON serializable"):
        json.dumps(node)


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

    with pytest.raises(asdf.exceptions.AsdfLazyReferenceError, match="Failed to resolve"):
        d["b"]


def test_lazy_tree_option(tmp_path):
    fn = tmp_path / "test.asdf"

    arr = np.arange(42)
    tree = {"a": {"b": arr}}
    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        assert isinstance(af["a"], AsdfDictNode)

    with asdf.open(fn, lazy_tree=False) as af:
        assert not isinstance(af["a"], AsdfDictNode)

    # test default (False)
    with asdf.open(fn) as af:
        assert not isinstance(af["a"], AsdfDictNode)

    with asdf.config_context() as cfg:
        cfg.lazy_tree = True
        with asdf.open(fn) as af:
            assert isinstance(af["a"], AsdfDictNode)
        cfg.lazy_tree = False
        with asdf.open(fn) as af:
            assert not isinstance(af["a"], AsdfDictNode)


def test_resolve_af_ref():
    with pytest.raises(asdf.exceptions.AsdfLazyReferenceError, match="Failed to resolve"):
        _resolve_af_ref(None)
    af = asdf.AsdfFile()
    af_ref = weakref.ref(af)
    assert _resolve_af_ref(af_ref) is af
    del af
    with pytest.raises(asdf.exceptions.AsdfLazyReferenceError, match="Failed to resolve"):
        _resolve_af_ref(af_ref)


@pytest.mark.parametrize(
    "NodeClass,data",
    [
        (AsdfDictNode, {1: "a", 2: "b"}),
        (AsdfListNode, [1, 2]),
        (AsdfOrderedDictNode, collections.OrderedDict({1: "a", 2: "b"})),
        (int, 1),  # a non-wrappable class
    ],
)
def test_to_lazy_node(NodeClass, data):
    node = _to_lazy_node(data, None)
    assert isinstance(node, NodeClass)
