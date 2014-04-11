# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io

from astropy.extern import six

from ..finf import FinfFile
from ..finftypes import FinfTypeIndex
from ..tags import FinfObject


def assert_tree_match(old_tree, new_tree):
    def recurse(old, new):
        old_type = FinfTypeIndex.get_finftype_from_custom_type(type(old))
        new_type = FinfTypeIndex.get_finftype_from_custom_type(type(new))

        if (old_type is not None and
            new_type is not None and
            old_type is new_type and
            hasattr(old_type, 'assert_equal')):
            old_type.assert_equal(old, new)
        elif isinstance(old, dict) and isinstance(new, dict):
            assert set(old.keys()) == set(new.keys())
            for key in old.keys():
                recurse(old[key], new[key])
        elif isinstance(old, (list, tuple)) and isinstance(new, (list, tuple)):
            assert len(old) == len(new)
            for a, b in zip(old, new):
                recurse(a, b)
        else:
            assert old == new

    recurse(old_tree, new_tree)


def assert_roundtrip_tree(
        tree, tmpdir, finf_check_func=None, raw_yaml_check_func=None):
    fname = str(tmpdir.join('test.finf'))

    # First, test writing/reading a BytesIO buffer
    buff = io.BytesIO()
    FinfFile(tree).write_to(buff)
    assert not buff.closed
    buff.seek(0)
    ff = FinfFile.read(buff)
    assert not buff.closed
    assert isinstance(ff.tree, FinfObject)
    assert_tree_match(tree, ff.tree)
    if finf_check_func:
        finf_check_func(ff)

    buff.seek(0)
    content = FinfFile.read_raw_tree(buff)
    # We *never* want to get any raw python objects out
    assert b'!!python' not in content
    assert b'!finf' in content
    assert content.startswith(b'%FINF ')
    if raw_yaml_check_func:
        raw_yaml_check_func(content)

    # Then, test writing/reading to a real file
    FinfFile(tree).write_to(fname)
    with FinfFile.read(fname) as ff:
        assert_tree_match(tree, ff.tree)
        if finf_check_func:
            finf_check_func(ff)


def yaml_to_finf(yaml_content, yaml_headers=True):
    if isinstance(yaml_content, six.text_type):
        yaml_content = yaml_content.encode('utf-8')

    buff = io.BytesIO()

    if yaml_headers:
        buff.write(b"""%FINF 0.1.0
%YAML 1.1
%TAG ! tag:stsci.edu:finf/0.1.0/
--- !finf
""")
    buff.write(yaml_content)
    if yaml_headers:
        buff.write(b"\n...\n")

    buff.seek(0)
    return buff
