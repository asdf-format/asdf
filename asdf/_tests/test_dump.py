"""
Test dump, dumps, load and loads

These are thin wrappers around AsdfFile
so the tests here will be relatively simple.
"""

from asdf import dump, dumps, load, loads
from asdf._tests._helpers import assert_tree_match


def test_roundtrip(tmp_path, tree):
    fn = tmp_path / "test.asdf"
    dump(tree, fn)
    rt = load(fn)
    assert_tree_match(tree, rt)


def test_str_roundtrip(tree):
    rt = loads(dumps(tree))
    assert_tree_match(tree, rt)
