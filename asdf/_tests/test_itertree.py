import copy

import pytest

from asdf import _itertree


def _traversal_to_generator(tree, traversal):
    if "modify" not in traversal.__name__:
        return traversal(tree)

    def make_generator(tree):
        values = []

        def callback(obj, edge):
            values.append((obj, edge))
            return obj

        traversal(tree, callback)
        yield from values

    return make_generator(tree)


@pytest.mark.parametrize(
    "traversal", [_itertree.breadth_first, _itertree.breadth_first_modify, _itertree.breadth_first_modify_and_copy]
)
def test_breadth_first_traversal(traversal):
    tree = {
        "a": {
            "b": [1, 2, {"c": 3}],
            "d": 4,
        },
        "e": [5, 6, [7, 8, {"f": 9}]],
    }
    # It is ok for results to come in any order as long as
    # all nodes closer to the root come before any more distant
    # node. Track those here by ordering expected results by 'layer'
    expected_results = [
        [
            tree,
        ],
        [tree["a"], tree["e"]],
        [tree["a"]["b"], tree["a"]["d"], tree["e"][0], tree["e"][1], tree["e"][2]],
        [tree["a"]["b"][0], tree["a"]["b"][1], tree["a"]["b"][2], tree["e"][2][0], tree["e"][2][1], tree["e"][2][2]],
        [tree["a"]["b"][2]["c"], tree["e"][2][2]["f"]],
    ]

    expected = []

    for node, edge in _traversal_to_generator(tree, traversal):
        if not len(expected):
            expected = expected_results.pop(0)
        assert node in expected
        expected.remove(node)
    assert not expected_results


@pytest.mark.parametrize(
    "traversal", [_itertree.breadth_first, _itertree.breadth_first_modify, _itertree.breadth_first_modify_and_copy]
)
def test_recursive_breadth_first_traversal(traversal):
    tree = {
        "a": {},
        "b": {},
    }
    tree["a"]["b"] = tree["b"]
    tree["b"]["a"] = tree["a"]

    expected_results = [
        [
            tree,
        ],
        [tree["a"], tree["b"]],
    ]

    expected = []
    for node, edge in _traversal_to_generator(tree, traversal):
        if not len(expected):
            expected = expected_results.pop(0)
        assert node in expected
        expected.remove(node)
    assert not expected_results


@pytest.mark.parametrize(
    "traversal", [_itertree.leaf_first, _itertree.leaf_first_modify, _itertree.leaf_first_modify_and_copy]
)
def test_leaf_first_traversal(traversal):
    tree = {
        "a": {
            "b": [1, 2, {"c": 3}],
            "d": 4,
        },
        "e": [5, 6, [7, 8, {"f": 9}]],
    }
    seen_keys = set()
    reverse_paths = {
        ("e", 2, 2, "f"): [("e", 2, 2), ("e", 2, 1), ("e", 2, 0)],
        ("e", 2, 2): [("e", 0), ("e", 1), ("e", 2)],
        ("e", 2, 1): [("e", 0), ("e", 1), ("e", 2)],
        ("e", 2, 0): [("e", 0), ("e", 1), ("e", 2)],
        ("e", 2): [("e",), ("a",)],
        ("e", 1): [("e",), ("a",)],
        ("e", 0): [("e",), ("a",)],
        ("e",): [()],
        ("a", "b", 2, "c"): [("a", "b", 0), ("a", "b", 1), ("a", "b", 2)],
        ("a", "b", 2): [("a", "b"), ("a", "d")],
        ("a", "b", 1): [("a", "b"), ("a", "d")],
        ("a", "b", 0): [("a", "b"), ("a", "d")],
        ("a", "b"): [("a",), ("e",)],
        ("a", "d"): [("a",), ("e",)],
        ("a",): [()],
        (): [],
    }
    expected = {
        ("e", 2, 2, "f"),
        ("a", "b", 2, "c"),
        ("a", "d"),
    }
    for node, edge in _traversal_to_generator(tree, traversal):
        keys = _itertree.edge_to_keys(edge)
        assert keys in expected
        obj = tree
        for key in keys:
            obj = obj[key]
        assert obj == node

        # updated expected
        seen_keys.add(keys)
        expected.remove(keys)
        for new_keys in reverse_paths[keys]:
            if new_keys in seen_keys:
                continue
            expected.add(new_keys)
    assert not expected


@pytest.mark.parametrize(
    "traversal", [_itertree.leaf_first, _itertree.leaf_first_modify, _itertree.leaf_first_modify_and_copy]
)
def test_recursive_leaf_first_traversal(traversal):
    tree = {
        "a": {},
        "b": {},
    }
    tree["a"]["b"] = tree["b"]
    tree["b"]["a"] = tree["a"]

    seen_keys = set()
    reverse_paths = {
        ("a", "b"): [("a",), ("b",)],
        ("b", "a"): [("a",), ("b",)],
        ("a",): [()],
        ("b",): [()],
        (): [],
    }
    expected = {
        ("a", "b"),
        ("b", "a"),
    }
    visits = []
    for node, edge in _traversal_to_generator(tree, traversal):
        keys = _itertree.edge_to_keys(edge)
        assert keys in expected
        obj = tree
        for key in keys:
            obj = obj[key]
        visits.append((obj, edge))

        # updated expected
        seen_keys.add(keys)
        expected.remove(keys)
        for new_keys in reverse_paths[keys]:
            if new_keys in seen_keys:
                continue
            expected.add(new_keys)
    assert len(visits) == 3


@pytest.mark.parametrize(
    "traversal", [_itertree.depth_first, _itertree.depth_first_modify, _itertree.depth_first_modify_and_copy]
)
def test_depth_first_traversal(traversal):
    tree = {
        "a": {
            "b": [1, 2, {"c": 3}],
            "d": 4,
        },
        "e": [5, 6, [7, 8, {"f": 9}]],
    }
    forward_paths = {
        (): [("a",), ("e",)],
        ("a",): [("a", "b"), ("a", "d")],
        ("a", "b"): [("a", "b", 0), ("a", "b", 1), ("a", "b", 2)],
        ("a", "b", 0): [],
        ("a", "b", 1): [],
        ("a", "b", 2): [("a", "b", 2, "c")],
        ("a", "b", 2, "c"): [],
        ("a", "d"): [],
        ("e",): [("e", 0), ("e", 1), ("e", 2)],
        ("e", 0): [],
        ("e", 1): [],
        ("e", 2): [("e", 2, 0), ("e", 2, 1), ("e", 2, 2)],
        ("e", 2, 0): [],
        ("e", 2, 1): [],
        ("e", 2, 2): [("e", 2, 2, "f")],
        ("e", 2, 2, "f"): [],
    }
    expected = {()}
    seen_keys = set()

    for node, edge in _traversal_to_generator(tree, traversal):
        keys = _itertree.edge_to_keys(edge)
        assert keys in expected
        obj = tree
        for key in keys:
            obj = obj[key]
        assert obj == node

        # updated expected
        seen_keys.add(keys)
        expected.remove(keys)
        for new_keys in forward_paths[keys]:
            if new_keys in seen_keys:
                continue
            expected.add(new_keys)
    assert not expected


@pytest.mark.parametrize(
    "traversal", [_itertree.depth_first, _itertree.depth_first_modify, _itertree.depth_first_modify_and_copy]
)
def test_recursive_depth_first_traversal(traversal):
    tree = {
        "a": {},
        "b": {},
    }
    tree["a"]["b"] = tree["b"]
    tree["b"]["a"] = tree["a"]

    seen_keys = set()
    forward_paths = {
        (): [("a",), ("b",)],
        ("a",): [("a", "b")],
        ("b",): [("b", "a")],
        ("a", "b"): [],
        ("b", "a"): [],
    }
    expected = {
        (),
    }
    visits = []
    for node, edge in _traversal_to_generator(tree, traversal):
        keys = _itertree.edge_to_keys(edge)
        assert keys in expected
        obj = tree
        for key in keys:
            obj = obj[key]
        visits.append((node, edge))

        # updated expected
        seen_keys.add(keys)
        expected.remove(keys)
        for new_keys in forward_paths[keys]:
            if new_keys in seen_keys:
                continue
            expected.add(new_keys)
    assert len(visits) == 3


def test_breadth_first_modify():
    tree = {
        "a": [1, 2, {"b": 3}],
        "c": {
            "d": [4, 5, 6],
        },
    }

    def callback(obj, keys):
        if isinstance(obj, list) and 1 in obj:
            return [1, 2, 3]
        if isinstance(obj, dict):
            assert "b" not in obj
        return obj

    _itertree.breadth_first_modify(tree, callback)
    assert tree["a"] == [1, 2, 3]


def test_depth_first_modify():
    tree = {
        "a": [1, 2, {"b": 3}],
        "c": {
            "d": [4, 5, 6],
        },
    }

    def callback(obj, keys):
        if isinstance(obj, dict) and "d" in obj:
            obj["d"] = [42]
        if isinstance(obj, list) and 42 in obj:
            assert len(obj) == 1
        return obj

    _itertree.depth_first_modify(tree, callback)
    assert tree["c"]["d"] == [42]


def test_leaf_first_modify():
    tree = {
        "a": [1, 2, {"b": 3}],
        "c": {
            "d": [4, 5, 6],
        },
    }

    def callback(obj, keys):
        if isinstance(obj, list) and 1 in obj:
            assert 42 in obj
        if isinstance(obj, dict) and "b" in obj:
            return 42
        return obj

    _itertree.leaf_first_modify(tree, callback)
    assert tree["a"] == [1, 2, 42]


def test_breadth_first_modify_and_copy():
    tree = {
        "a": [1, 2, {"b": 3}],
        "c": {
            "d": [4, 5, 6],
        },
    }

    def callback(obj, keys):
        if isinstance(obj, list) and 1 in obj:
            assert 42 not in obj
        if isinstance(obj, dict) and "b" in obj:
            return 42
        return obj

    # copy the tree to make sure it's not modified
    copied_tree = copy.deepcopy(tree)
    result = _itertree.breadth_first_modify_and_copy(copied_tree, callback)
    assert result["a"] == [1, 2, 42]
    assert copied_tree == tree


def test_depth_first_modify_and_copy():
    tree = {
        "a": [1, 2, {"b": 3}],
        "c": {
            "d": [4, 5, 6],
        },
    }

    def callback(obj, keys):
        if isinstance(obj, list) and 1 in obj:
            assert 42 not in obj
        if isinstance(obj, dict) and "b" in obj:
            return 42
        return obj

    # copy the tree to make sure it's not modified
    copied_tree = copy.deepcopy(tree)
    result = _itertree.depth_first_modify_and_copy(copied_tree, callback)
    assert result["a"] == [1, 2, 42]
    assert copied_tree == tree


def test_leaf_first_modify_and_copy():
    tree = {
        "a": [1, 2, {"b": 3}],
        "c": {
            "d": [4, 5, 6],
        },
    }

    def callback(obj, keys):
        if isinstance(obj, list) and 1 in obj:
            assert 42 in obj
        if isinstance(obj, dict) and "b" in obj:
            return 42
        return obj

    # copy the tree to make sure it's not modified
    copied_tree = copy.deepcopy(tree)
    result = _itertree.leaf_first_modify_and_copy(copied_tree, callback)
    assert result["a"] == [1, 2, 42]
    assert copied_tree == tree


@pytest.mark.parametrize(
    "traversal",
    [
        _itertree.breadth_first_modify,
        _itertree.depth_first_modify,
        _itertree.leaf_first_modify,
        _itertree.breadth_first_modify_and_copy,
        _itertree.depth_first_modify_and_copy,
        _itertree.leaf_first_modify_and_copy,
    ],
)
def test_node_removal(traversal):
    tree = {
        "a": [1, 2, 3],
        "b": 4,
    }

    def callback(obj, edge):
        if obj in (1, 3, 4):
            return _itertree.RemoveNode
        return obj

    result = traversal(tree, callback)
    if result is not None:  # this is a copy
        original = tree
    else:
        original = None
        result = tree
    assert result["a"] == [
        2,
    ]
    assert "b" not in result
    if original is not None:
        assert original["a"] == [1, 2, 3]
        assert original["b"] == 4
        assert set(original.keys()) == {"a", "b"}


@pytest.mark.parametrize(
    "traversal",
    [
        _itertree.breadth_first_modify,
        _itertree.depth_first_modify,
        _itertree.leaf_first_modify,
        _itertree.breadth_first_modify_and_copy,
        _itertree.depth_first_modify_and_copy,
        _itertree.leaf_first_modify_and_copy,
    ],
)
def test_key_order(traversal):
    """
    All traversal and modification functions should preserve
    the order of keys in a dictionary
    """
    tree = {}
    tree["a"] = [1, 2]
    tree["b"] = [3, 4]
    tree["c"] = {}
    tree["c"]["d"] = [5, 6]
    tree["c"]["e"] = [7, 8]

    result = traversal(tree, lambda obj, edge: obj)
    if result is None:
        result = tree

    assert list(result.keys()) == ["a", "b", "c"]
    assert result["a"] == [1, 2]
    assert result["b"] == [3, 4]
    assert list(result["c"].keys()) == ["d", "e"]
    assert result["c"]["d"] == [5, 6]
    assert result["c"]["e"] == [7, 8]


@pytest.mark.parametrize(
    "traversal",
    [
        _itertree.breadth_first_modify,
        _itertree.depth_first_modify,
        _itertree.leaf_first_modify,
        _itertree.breadth_first_modify_and_copy,
        _itertree.depth_first_modify_and_copy,
        _itertree.leaf_first_modify_and_copy,
    ],
)
def test_cache_callback(traversal):
    class Foo:
        pass

    obj = Foo()
    obj.count = 0

    tree = {}
    tree["a"] = obj
    tree["b"] = obj
    tree["c"] = {"d": obj}

    def callback(obj, edge):
        if isinstance(obj, Foo):
            obj.count += 1
        return obj

    result = traversal(tree, callback)
    if result is None:
        result = tree

    assert result["a"].count == 1
    assert result["b"].count == 1
    assert result["c"]["d"].count == 1


@pytest.mark.parametrize(
    "traversal",
    [
        _itertree.breadth_first_modify,
        _itertree.depth_first_modify,
        _itertree.leaf_first_modify,
        _itertree.breadth_first_modify_and_copy,
        _itertree.depth_first_modify_and_copy,
        _itertree.leaf_first_modify_and_copy,
    ],
)
def test_recursive_object(traversal):
    tree = {}
    tree["a"] = {"count": 0}
    tree["b"] = {"a": tree["a"]}
    tree["a"]["b"] = tree["b"]

    def callback(obj, edge):
        if isinstance(obj, dict) and "count" in obj:
            obj["count"] += 1
        return obj

    result = traversal(tree, callback)
    if result is None:
        result = tree

    assert result["a"]["count"] == 1
    assert result["b"]["a"]["count"] == 1
    assert result["a"] is result["b"]["a"]
