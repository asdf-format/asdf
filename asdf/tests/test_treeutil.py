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
