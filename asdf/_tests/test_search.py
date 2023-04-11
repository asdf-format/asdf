import re

import numpy as np
import pytest

from asdf import AsdfFile


@pytest.fixture()
def asdf_file():
    tree = {
        "foo": 42,
        "nested": {"foo": 24, "foible": "whoops", "folicle": "yup", "moo": 24},
        "bar": "hello",
        "list": [{"index": 0}, {"index": 1}, {"index": 2}],
    }
    return AsdfFile(tree)


def test_no_arguments(asdf_file):
    result = asdf_file.search()
    assert len(result.paths) == 15
    assert len(result.nodes) == 15


def test_repr(asdf_file):
    result = asdf_file.search()
    assert "foo" in repr(result)
    assert "nested" in repr(result)
    assert "bar" in repr(result)
    assert "list" in repr(result)


def test_single_result(asdf_file):
    result = asdf_file.search("bar")
    assert len(result.paths) == 1
    assert len(result.nodes) == 1
    assert result.node == "hello"
    assert result.path == "root['bar']"
    result.replace("goodbye")
    assert asdf_file["bar"] == "goodbye"


def test_multiple_results(asdf_file):
    result = asdf_file.search("foo")
    assert len(result.paths) == 2
    assert len(result.nodes) == 2
    assert 42 in result.nodes
    assert 24 in result.nodes
    assert "root['foo']" in result.paths
    assert "root['nested']['foo']" in result.paths

    with pytest.raises(RuntimeError, match=r"More than one result"):
        result.path

    with pytest.raises(RuntimeError, match=r"More than one result"):
        result.node

    result.replace(54)
    assert asdf_file["foo"] == 54
    assert asdf_file["nested"]["foo"] == 54


def test_by_key(asdf_file):
    result = asdf_file.search("bar")
    assert result.node == "hello"

    result = asdf_file.search("^b.r$")
    assert result.node == "hello"

    result = asdf_file.search(re.compile("fo[oi]"))
    assert set(result.nodes) == {42, 24, "whoops"}

    result = asdf_file.search(0)
    assert result.node == {"index": 0}


def test_by_type(asdf_file):
    result = asdf_file.search(type_=str)
    assert sorted(result.nodes) == sorted(["hello", "whoops", "yup"])

    result = asdf_file.search(type_="int")
    assert result.nodes == [42, 24, 24, 0, 1, 2]

    result = asdf_file.search(type_="dict|list")
    assert len(result.nodes) == 5

    result = asdf_file.search(type_=re.compile("^i.t$"))
    assert result.nodes == [42, 24, 24, 0, 1, 2]

    with pytest.raises(TypeError, match=r"type must be .*"):
        asdf_file.search(type_=4)


def test_by_value(asdf_file):
    result = asdf_file.search(value=42)
    assert result.node == 42


def test_by_value_with_ndarray():
    """
    Check some edge cases when comparing integers and booleans to numpy arrays.
    """
    tree = {"foo": np.arange(10)}
    af = AsdfFile(tree)
    result = af.search(value=True)
    assert len(result.nodes) == 0
    result = af.search(value=42)
    assert len(result.nodes) == 0


def test_by_filter(asdf_file):
    with pytest.raises(ValueError, match=r"filter must accept 1 or 2 arguments"):
        asdf_file.search(filter_=lambda: True)

    result = asdf_file.search(filter_=lambda n: isinstance(n, int) and n % 2 == 0)
    assert result.nodes == [42, 24, 24, 0, 2]

    result = asdf_file.search(filter_=lambda n, k: k == "foo" and n > 30)
    assert result.node == 42


def test_multiple_conditions(asdf_file):
    result = asdf_file.search("foo", value=24)
    assert len(result.nodes) == 1
    assert result.node == 24
    result.replace(19)
    assert len(result.nodes) == 0
    assert asdf_file["foo"] == 42
    assert asdf_file["nested"]["foo"] == 19


def test_chaining(asdf_file):
    result = asdf_file.search("foo").search(value=24)
    assert len(result.nodes) == 1
    assert result.node == 24
    result.replace(19)
    assert len(result.nodes) == 0
    assert asdf_file["foo"] == 42
    assert asdf_file["nested"]["foo"] == 19


def test_index_operator(asdf_file):
    result = asdf_file.search()["nested"].search("foo")
    assert len(result.nodes) == 1
    assert result.node == 24

    with pytest.raises(TypeError, match=r"This node cannot be indexed"):
        asdf_file.search()["foo"][0]


def test_format(asdf_file):
    result = asdf_file.search()
    original_len = len(repr(result).split("\n"))

    result = result.format(max_rows=original_len - 5)
    new_len = len(repr(result).split("\n"))
    assert new_len < original_len

    result = result.format(max_rows=(None, 5))
    new_len = len(repr(result).split("\n"))
    assert new_len < original_len

    assert repr(result) == repr(result.format())


def test_no_results(asdf_file):
    result = asdf_file.search("missing")
    assert len(result.nodes) == 0
    assert "No results found." in repr(result)
    assert result.node is None
    assert result.path is None
    # Testing no exceptions here:
    result.replace("foo")


def test_recursive_tree():
    tree = {"foo": {"bar": "baz"}}
    af = AsdfFile(tree)
    af.tree["foo"]["nested"] = af.tree["foo"]

    result = af.search()
    assert "(recursive reference)" in repr(result)

    result = af.search("bar")
    assert len(result.nodes) == 1
    assert result.node == "baz"

    result.replace("zap")
    assert af["foo"]["bar"] == "zap"
    assert af["foo"]["nested"]["bar"] == "zap"


def test_search():
    tree = {"foo": 42, "bar": "hello", "baz": np.arange(20)}
    af = AsdfFile(tree)

    result = af.search("foo")
    assert result.node == 42

    result = af.search(type_="ndarray")
    assert (result.node == tree["baz"]).all()

    result = af.search(value="hello")
    assert result.node == "hello"
