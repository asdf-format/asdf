# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io

import numpy as np

from astropy.extern import six
from astropy import units as u
from astropy.utils.compat.odict import OrderedDict
from astropy.tests.helper import pytest

import yaml

from .. import finf
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

    def check_finf(finf):
        tree = finf.tree

        assert isinstance(tree['ordered_dict'], OrderedDict)
        assert list(tree['ordered_dict'].keys()) == ['first', 'second', 'third']

        assert not isinstance(tree['unordered_dict'], OrderedDict)
        assert isinstance(tree['unordered_dict'], dict)

    def check_raw_yaml(content):
        assert b'OrderedDict' not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)


def test_unicode_write(tmpdir):
    # We want to write unicode out as regular utf-8-encoded
    # characters, not as escape sequences

    tree = {
        "ɐʇɐp‾ǝpoɔıun": 42,
        "ascii_only": "this is ascii"
    }

    def check_finf(finf):
        assert "ɐʇɐp‾ǝpoɔıun" in finf.tree
        assert isinstance(finf.tree['ascii_only'], six.text_type)

    def check_raw_yaml(content):
        # Ensure that unicode is written out as UTF-8 without escape
        # sequences
        assert "ɐʇɐp‾ǝpoɔıun".encode('utf-8') in content
        # Ensure that the unicode "tag" is not used
        assert b"unicode" not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)


def test_arbitrary_python_object():
    # Putting "just any old" Python object in the tree should raise an
    # exception.

    class Foo(object):
        pass

    tree = {'object': Foo()}

    buff = io.BytesIO()
    ff = finf.FinfFile(tree)
    with pytest.raises(yaml.YAMLError):
        ff.write_to(buff)


def test_python_tuple(tmpdir):
    # We don't want to store tuples as tuples, because that's not a
    # built-in YAML data type.  This test ensures that they are
    # converted to lists.

    tree = {
        "val": (1, 2, 3)
    }

    def check_finf(finf):
        assert isinstance(finf.tree['val'], list)

    def check_raw_yaml(content):
        assert b'tuple' not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)


def test_tags_removed_after_load(tmpdir):
    tree = {
        "foo": ["bar", (1, 2, None)]
        }

    def check_finf(finf):
        def assert_untagged(node):
            if node != finf.tree:
                assert not isinstance(node, tagged.Tagged)

        treeutil.walk(finf.tree, assert_untagged)

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf)


def test_explicit_tags():

    yaml = """%FINF 0.1.0
%YAML 1.1
--- !<tag:stsci.edu:finf/0.1.0/core/finf>
unit: !<tag:stsci.edu:finf/0.1.0/unit/unit> m
...
    """
    # Check that fully-qualified explicit tags work

    buff = helpers.yaml_to_finf(yaml, yaml_headers=False)
    ff = finf.FinfFile.read(buff)

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
    ff = finf.FinfFile(tree).write_to(buff)
    buff.seek(0)
    ff = finf.FinfFile().read(buff)

    assert np.isnan(ff.tree['a'])
    assert np.isinf(ff.tree['b'])
    assert np.isinf(ff.tree['c'])
