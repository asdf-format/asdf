from asdf import treeutil


def test_get_children():
    parent = ["foo", "bar"]
    assert treeutil.get_children(parent) == [(0, "foo"), (1, "bar")]

    parent = ("foo", "bar")
    assert treeutil.get_children(parent) == [(0, "foo"), (1, "bar")]

    parent = {"foo": "bar", "ding": "dong"}
    assert sorted(treeutil.get_children(parent)) == sorted([("foo", "bar"), ("ding", "dong")])

    parent = "foo"
    assert treeutil.get_children(parent) == []

    parent = None
    assert treeutil.get_children(parent) == []


def test_is_container():
    for value in [[], {}, tuple()]:
        assert treeutil.is_container(value) is True

    for value in ["foo", 12, 13.9827]:
        assert treeutil.is_container(value) is False


def test_walk_and_modify_shared_references():
    target = {"foo": "bar"}
    nested_in_dict = {"target": target}
    nested_in_list = [target]
    tree = {"target": target, "nested_in_dict": nested_in_dict, "nested_in_list": nested_in_list}

    assert tree["target"] is tree["nested_in_dict"]["target"]
    assert tree["target"] is tree["nested_in_list"][0]

    def _callback(node):
        if "foo" in node:
            return {"foo": "baz"}
        else:
            return node

    result = treeutil.walk_and_modify(tree, _callback)

    assert result is not tree
    assert result["target"] is not target
    assert result["target"]["foo"] == "baz"
    assert result["target"] is result["nested_in_dict"]["target"]
    assert result["target"] is result["nested_in_list"][0]
