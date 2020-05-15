# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import io
from collections import namedtuple, OrderedDict
from typing import NamedTuple

import numpy as np

import pytest

import yaml

import asdf
from asdf import tagged
from asdf import treeutil
from asdf import yamlutil
from asdf.compat.numpycompat import NUMPY_LT_1_14

from . import helpers


def test_ordered_dict(tmpdir):
    # Test that we can write out and read in ordered dicts.

    tree = {
        "ordered_dict": OrderedDict(
            [('first', 'foo'),
             ('second', 'bar'),
             ('third', 'baz')]),

        "unordered_dict": {
            'first': 'foo',
            'second': 'bar',
            'third': 'baz'
        }
    }

    def check_asdf(asdf):
        tree = asdf.tree

        assert isinstance(tree['ordered_dict'], OrderedDict)
        assert list(tree['ordered_dict'].keys()) == ['first', 'second', 'third']

        assert not isinstance(tree['unordered_dict'], OrderedDict)
        assert isinstance(tree['unordered_dict'], dict)

    def check_raw_yaml(content):
        assert b'OrderedDict' not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf,
                                  raw_yaml_check_func=check_raw_yaml)


def test_unicode_write(tmpdir):
    # We want to write unicode out as regular utf-8-encoded
    # characters, not as escape sequences

    tree = {
        "ɐʇɐp‾ǝpoɔıun": 42,
        "ascii_only": "this is ascii"
    }

    def check_asdf(asdf):
        assert "ɐʇɐp‾ǝpoɔıun" in asdf.tree
        assert isinstance(asdf.tree['ascii_only'], str)

    def check_raw_yaml(content):
        # Ensure that unicode is written out as UTF-8 without escape
        # sequences
        assert "ɐʇɐp‾ǝpoɔıun".encode('utf-8') in content
        # Ensure that the unicode "tag" is not used
        assert b"unicode" not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf,
                                  raw_yaml_check_func=check_raw_yaml)


def test_arbitrary_python_object():
    # Putting "just any old" Python object in the tree should raise an
    # exception.

    class Foo:
        pass

    tree = {'object': Foo()}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    with pytest.raises(yaml.YAMLError):
        ff.write_to(buff)


def run_tuple_test(tree, tmpdir):
    def check_asdf(asdf):
        assert isinstance(asdf.tree['val'], list)

    def check_raw_yaml(content):
        assert b'tuple' not in content

    # Ignore these warnings for the tests that don't actually test the warning
    init_options = dict(ignore_implicit_conversion=True)

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf,
                                  raw_yaml_check_func=check_raw_yaml,
                                  init_options=init_options)


def test_python_tuple(tmpdir):
    # We don't want to store tuples as tuples, because that's not a
    # built-in YAML data type.  This test ensures that they are
    # converted to lists.

    tree = {
        "val": (1, 2, 3)
    }

    run_tuple_test(tree, tmpdir)


def test_named_tuple_collections(tmpdir):
    # Ensure that we are able to serialize a collections.namedtuple.

    nt = namedtuple("TestNamedTuple1", ("one", "two", "three"))

    tree = {
        "val": nt(1, 2, 3)
    }

    run_tuple_test(tree, tmpdir)

def test_named_tuple_typing(tmpdir):
    # Ensure that we are able to serialize a typing.NamedTuple.

    nt = NamedTuple("TestNamedTuple2",
                    (("one", int), ("two", int), ("three", int)))
    tree = {
        "val": nt(1, 2, 3)
    }

    run_tuple_test(tree, tmpdir)


def test_named_tuple_collections_recursive(tmpdir):
    nt = namedtuple("TestNamedTuple3", ("one", "two", "three"))

    tree = {
        "val": nt(1, 2, np.ones(3))
    }

    def check_asdf(asdf):
        assert (asdf.tree['val'][2] == np.ones(3)).all()

    init_options = dict(ignore_implicit_conversion=True)
    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf,
                                  init_options=init_options)


def test_named_tuple_typing_recursive(tmpdir):
    nt = NamedTuple("TestNamedTuple4",
                    (("one", int), ("two", int), ("three", np.ndarray)))

    tree = {
        "val": nt(1, 2, np.ones(3))
    }

    def check_asdf(asdf):
        assert (asdf.tree['val'][2] == np.ones(3)).all()

    init_options = dict(ignore_implicit_conversion=True)
    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf,
                                  init_options=init_options)


def test_implicit_conversion_warning():
    nt = namedtuple("TestTupleWarning", ("one", "two", "three"))

    tree = {
        "val": nt(1, 2, np.ones(3))
    }

    with pytest.warns(UserWarning, match="Failed to serialize instance"):
        with asdf.AsdfFile(tree):
            pass

    with pytest.warns(None) as w:
        with asdf.AsdfFile(tree, ignore_implicit_conversion=True):
            assert len(w) == 0


@pytest.mark.xfail(reason='pyyaml has a bug and does not support tuple keys')
def test_python_tuple_key(tmpdir):
    """
    This tests whether tuple keys are round-tripped properly.

    As of this writing, this does not work in pyyaml but does work in
    ruamel.yaml. If/when we decide to switch to ruamel.yaml, this test should
    pass.
    """
    tree = { (42, 1): 'foo' }
    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_tags_removed_after_load(tmpdir):
    tree = {
        "foo": ["bar", (1, 2, None)]
        }

    def check_asdf(asdf):
        for node in treeutil.iter_tree(asdf.tree):
            if node != asdf.tree:
                assert not isinstance(node, tagged.Tagged)

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf)


def test_explicit_tags():
    yaml = """#ASDF {}
%YAML 1.1
--- !<tag:stsci.edu:asdf/core/asdf-1.0.0>
foo: !<tag:stsci.edu:asdf/core/ndarray-1.0.0> [1, 2, 3]
...
    """.format(asdf.versioning.default_version)

    # Check that fully qualified explicit tags work
    buff = helpers.yaml_to_asdf(yaml, yaml_headers=False)

    with asdf.open(buff) as ff:
        assert all(ff.tree['foo'] == [1, 2, 3])


def test_yaml_internal_reference(tmpdir):
    # Test that YAML internal references (anchors and aliases) work,
    # as well as recursive data structures.

    d = {
        'foo': '2',
        }
    d['bar'] = d

    l = []
    l.append(l)

    tree = {
        'first': d,
        'second': d,
        'list': l
    }

    def check_yaml(content):
        assert b'list:&id002-*id002' in b''.join(content.split())
    helpers.assert_roundtrip_tree(tree, tmpdir, raw_yaml_check_func=check_yaml)


def test_yaml_nan_inf():
    tree = {
        'a': np.nan,
        'b': np.inf,
        'c': -np.inf
        }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    buff.seek(0)
    with asdf.open(buff) as ff:
        assert np.isnan(ff.tree['a'])
        assert np.isinf(ff.tree['b'])
        assert np.isinf(ff.tree['c'])


def test_tag_object():
    class SomeObject:
        pass

    tag = 'tag:nowhere.org:none/some/thing'
    instance = tagged.tag_object(tag, SomeObject())
    assert instance._tag == tag


@pytest.mark.parametrize("numpy_value,expected_value", [
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
])
def test_numpy_scalar(numpy_value, expected_value):
    ctx = asdf.AsdfFile()
    tree = {"value": numpy_value}
    buffer = io.BytesIO()

    yamlutil.dump_tree(tree, buffer, ctx)
    buffer.seek(0)

    if isinstance(expected_value, float) and NUMPY_LT_1_14:
        assert yamlutil.load_tree(buffer, ctx)["value"] == pytest.approx(expected_value, rel=0.001)
    else:
        assert yamlutil.load_tree(buffer, ctx)["value"] == expected_value
