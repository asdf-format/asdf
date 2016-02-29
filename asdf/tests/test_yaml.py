# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True

import numpy as np

import pytest

import six

import yaml

from .. import asdf
from ..compat.odict import OrderedDict
from .. import tagged
from .. import treeutil

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

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf, check_raw_yaml)


def test_unicode_write(tmpdir):
    # We want to write unicode out as regular utf-8-encoded
    # characters, not as escape sequences

    tree = {
        "ɐʇɐp‾ǝpoɔıun": 42,
        "ascii_only": "this is ascii"
    }

    def check_asdf(asdf):
        assert "ɐʇɐp‾ǝpoɔıun" in asdf.tree
        assert isinstance(asdf.tree['ascii_only'], six.text_type)

    def check_raw_yaml(content):
        # Ensure that unicode is written out as UTF-8 without escape
        # sequences
        assert "ɐʇɐp‾ǝpoɔıun".encode('utf-8') in content
        # Ensure that the unicode "tag" is not used
        assert b"unicode" not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf, check_raw_yaml)


def test_arbitrary_python_object():
    # Putting "just any old" Python object in the tree should raise an
    # exception.

    class Foo(object):
        pass

    tree = {'object': Foo()}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    with pytest.raises(yaml.YAMLError):
        ff.write_to(buff)


def test_python_tuple(tmpdir):
    # We don't want to store tuples as tuples, because that's not a
    # built-in YAML data type.  This test ensures that they are
    # converted to lists.

    tree = {
        "val": (1, 2, 3)
    }

    def check_asdf(asdf):
        assert isinstance(asdf.tree['val'], list)

    def check_raw_yaml(content):
        assert b'tuple' not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf, check_raw_yaml)


def test_tags_removed_after_load(tmpdir):
    tree = {
        "foo": ["bar", (1, 2, None)]
        }

    def check_asdf(asdf):
        for node in treeutil.iter_tree(asdf.tree):
            if node != asdf.tree:
                assert not isinstance(node, tagged.Tagged)

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_explicit_tags():

    yaml = """#ASDF 1.0.0
%YAML 1.1
--- !<tag:stsci.edu:asdf/core/asdf-1.0.0>
unit: !<tag:stsci.edu:asdf/unit/unit-1.0.0> m
...
    """
    from astropy import units as u

    # Check that fully-qualified explicit tags work

    buff = helpers.yaml_to_asdf(yaml, yaml_headers=False)
    ff = asdf.AsdfFile.open(buff)

    assert isinstance(ff.tree['unit'], u.UnitBase)


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
        assert b'list:--&id002-*id002' in b''.join(content.split())

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
    with asdf.AsdfFile.open(buff) as ff:
        assert np.isnan(ff.tree['a'])
        assert np.isinf(ff.tree['b'])
        assert np.isinf(ff.tree['c'])
