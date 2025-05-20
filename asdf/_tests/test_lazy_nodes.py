import collections
import copy
import gc
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
        (AsdfDictNode, {"a": 1}, collections.abc.Mapping),
        (AsdfListNode, [1, 2], collections.abc.Sequence),
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
    assert type(node.tagged) is base


@pytest.mark.parametrize(
    "node,base_type",
    [
        (AsdfDictNode({"a": 1, "b": 2}), dict),
        (AsdfListNode([1, 2, 3]), list),
        (AsdfOrderedDictNode({"a": 1, "b": 2}), collections.OrderedDict),
    ],
)
@pytest.mark.parametrize("copy_operation", [copy.copy, copy.deepcopy])
def test_copy(node, base_type, copy_operation):
    copied_node = copy_operation(node)
    if copy_operation is copy.copy:
        assert type(copied_node) is type(node)
    else:
        assert type(copied_node) is base_type
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


def test_cache_clear_on_close(tmp_path):
    fn = tmp_path / "test.asdf"

    arr = np.arange(42)
    tree = {"a": arr}
    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        # grab a weakref to this array, it should fail
        # to resolve after the with exits
        ref = weakref.ref(af["a"])

    gc.collect()
    assert ref() is None


def test_access_after_del(tmp_path):
    fn = tmp_path / "test.asdf"

    arr = np.arange(42)
    tree = {"a": {"b": arr}}
    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        d = af["a"]

    del af
    gc.collect(2)

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
    gc.collect(2)

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


def test_lazy_node_treeutil_support():
    af = asdf.AsdfFile()
    af_ref = weakref.ref(af)
    tree = {
        "ordered_dict": AsdfOrderedDictNode({"a": 1}, af_ref),
        "dict": AsdfDictNode({"b": 2}, af_ref),
        "list": AsdfListNode([3, 4], af_ref),
    }
    seen_ints = set()

    def callback(node):
        if isinstance(node, int):
            seen_ints.add(node)

    asdf.treeutil.walk_and_modify(tree, callback)

    assert seen_ints == set([1, 2, 3, 4])


@pytest.fixture()
def cache_test_tree_path(tmp_path):
    my_array = np.arange(3, dtype="uint8")
    my_list = [my_array, my_array]
    tree = {"a": my_list, "b": my_list}
    af = asdf.AsdfFile(tree)
    fn = tmp_path / "test.asdf"
    af.write_to(fn)
    return fn


def test_cache_resolves_ref(cache_test_tree_path):
    with asdf.open(cache_test_tree_path, lazy_tree=True) as af:
        # since 'a' and 'b' were the same list when the file was saved
        # they should be the same list on read
        assert af["a"] is af["b"]
        # same for the arrays in the list
        assert af["a"][0] is af["a"][1]


def test_cache_frees_deleted_object(cache_test_tree_path):
    with asdf.open(cache_test_tree_path, lazy_tree=True) as af:
        # load 1 of the 2 lists
        l0 = af["a"]
        # grab a weakref to the list (to not hold onto the list)
        lref = weakref.ref(l0)
        # now delete all references to the list (including the one in the tree)
        del l0, af.tree["a"]
        # trigger garbage collection
        gc.collect(2)
        # check that the weakref fails to resolve (so the list was freed)
        assert lref() is None
        # and we can no longer access 'a'
        with pytest.raises(KeyError, match="'a'"):
            af["a"]
        # but can get 'b'
        assert af["b"][0] is af["b"][1]


def test_cache_non_weakref():
    """
    Test that an object that cannot weak reference can be cached
    """
    tagged_node = {}
    obj = complex(1, 1)
    cache_item = asdf.lazy_nodes._TaggedObjectCacheItem(tagged_node, obj)
    del obj
    gc.collect(2)
    assert cache_item.custom_object == complex(1, 1)


@pytest.fixture(params=[True, False, None], ids=["lazy", "not-lazy", "undefined"])
def lazy_test_class(request):
    class Foo:
        def __init__(self, data):
            self.data = data

    tag_uri = "asdf://somewhere.org/tags/foo-1.0.0"

    class FooConverter:
        tags = [tag_uri]
        types = [Foo]

        def to_yaml_tree(self, obj, tag, ctx):
            return obj.data

        def from_yaml_tree(self, node, tag, ctx):
            return Foo(node)

    lazy = request.param
    if lazy is not None:
        FooConverter.lazy = lazy
    # also set lazy on the class to pass it to the test
    Foo.lazy = lazy

    class FooExtension:
        extension_uri = "asdf://somewhere.org/extensions/minimum-1.0.0"
        converters = [FooConverter()]
        tags = [tag_uri]

    with asdf.config_context() as cfg:
        cfg.add_extension(FooExtension())
        yield Foo


def test_lazy_converter(tmp_path, lazy_test_class):
    obj = lazy_test_class({"a": 1})

    fn = tmp_path / "test.asdf"

    af = asdf.AsdfFile({"obj": obj})
    af.write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        if lazy_test_class.lazy is None or not lazy_test_class.lazy:
            target_class = dict
        else:
            target_class = AsdfDictNode
        assert isinstance(af["obj"].data, target_class)


@pytest.fixture()
def lazy_generator_class(request):

    class Foo:
        def __init__(self, data=None):
            self.data = data or {}

    tag_uri = "asdf://somewhere.org/tags/foo-1.0.0"

    class FooConverter:
        tags = [tag_uri]
        types = [Foo]
        lazy = True

        def to_yaml_tree(self, obj, tag, ctx):
            return obj.data

        def from_yaml_tree(self, node, tag, ctx):
            obj = Foo()
            yield obj
            obj.data = node

    class FooExtension:
        extension_uri = "asdf://somewhere.org/extensions/minimum-1.0.0"
        converters = [FooConverter()]
        tags = [tag_uri]

    with asdf.config_context() as cfg:
        cfg.add_extension(FooExtension())
        yield Foo


def test_lazy_generator_converter(tmp_path, lazy_generator_class):
    """
    Test that a converter that returns a generator is not lazy
    (even if it's marked as lazy).
    """
    obj = lazy_generator_class({"a": 1})

    fn = tmp_path / "test.asdf"

    af = asdf.AsdfFile({"obj": obj})
    af.write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        assert isinstance(af["obj"].data, dict)


def test_lazy_copy(tmp_path):
    """
    Test that copying an AsdfFile instance with a lazy
    tree doesn't result in the copy retaining references
    to the instance.
    """
    fn = tmp_path / "test.asdf"
    obj = asdf.tags.core.IntegerType(1)
    tree = {"a": {"b": obj}}
    # make a recursive structure
    tree["a"]["c"] = tree["a"]

    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn, lazy_tree=True) as af:
        af2 = af.copy()

    del af
    gc.collect(2)
    assert af2["a"]["b"] == obj
    assert af2["a"]["c"]["b"] is af2["a"]["b"]
