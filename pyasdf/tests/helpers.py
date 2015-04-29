# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

from astropy.extern import six

from ..asdf import AsdfFile
from ..asdftypes import _all_asdftypes

from ..tags.core import AsdfObject


def assert_tree_match(old_tree, new_tree, funcname='assert_equal'):
    """
    Assert that two ASDF trees match.

    Parameters
    ----------
    old_tree : ASDF tree

    new_tree : ASDF tree

    funcname : string
        The name of a method on members of old_tree and new_tree that
        will be used to compare custom objects.  The default of
        `assert_equal` handles Numpy arrays.
    """
    seen = set()

    def recurse(old, new):
        if id(old) in seen or id(new) in seen:
            return
        seen.add(id(old))
        seen.add(id(new))

        old_type = _all_asdftypes.from_custom_type(type(old))
        new_type = _all_asdftypes.from_custom_type(type(new))

        if (old_type is not None and
            new_type is not None and
            old_type is new_type and
            hasattr(old_type, funcname)):
            getattr(old_type, funcname)(old, new)
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
        tree, tmpdir, asdf_check_func=None, raw_yaml_check_func=None,
        write_options={}):
    """
    Assert that a given tree saves to ASDF and, when loaded back,
    the tree matches the original tree.

    tree : ASDF tree

    tmpdir : str
        Path to temporary directory to save file

    asdf_check_func : callable, optional
        Will be called with the reloaded ASDF file to perform any
        additional checks.

    raw_yaml_check_func : callable, optional
        Will be called with the raw YAML content as a string to
        perform any additional checks.
    """
    fname = str(tmpdir.join('test.asdf'))

    # First, test writing/reading a BytesIO buffer
    buff = io.BytesIO()
    AsdfFile(tree).write_to(buff, **write_options)
    assert not buff.closed
    buff.seek(0)
    with AsdfFile.open(buff, mode='rw') as ff:
        assert not buff.closed
        assert isinstance(ff.tree, AsdfObject)
        assert_tree_match(tree, ff.tree)
        if asdf_check_func:
            asdf_check_func(ff)

    buff.seek(0)
    content = AsdfFile.open(buff, _get_yaml_content=True)
    buff.close()
    # We *never* want to get any raw python objects out
    assert b'!!python' not in content
    assert b'!core/asdf' in content
    assert content.startswith(b'%YAML 1.1')
    if raw_yaml_check_func:
        raw_yaml_check_func(content)

    # Then, test writing/reading to a real file
    ff = AsdfFile(tree)
    ff.write_to(fname, **write_options)
    with AsdfFile.open(fname, mode='rw') as ff:
        assert_tree_match(tree, ff.tree)
        if asdf_check_func:
            asdf_check_func(ff)


def yaml_to_asdf(yaml_content, yaml_headers=True):
    """
    Given a string of YAML content, adds the extra pre-
    and post-amble to make it an ASDF file.

    Parameters
    ----------
    yaml_content : string

    yaml_headers : bool, optional
        When True (default) add the standard ASDF YAML headers.

    Returns
    -------
    buff : io.BytesIO()
        A file-like object containing the ASDF-like content.
    """
    if isinstance(yaml_content, six.text_type):
        yaml_content = yaml_content.encode('utf-8')

    buff = io.BytesIO()

    if yaml_headers:
        buff.write(b"""#ASDF 0.1.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/0.1.0/
--- !core/asdf
""")
    buff.write(yaml_content)
    if yaml_headers:
        buff.write(b"\n...\n")

    buff.seek(0)
    return buff


def get_file_sizes(dirname):
    """
    Get the file sizes in a directory.

    Parameters
    ----------
    dirname : string
        Path to a directory

    Returns
    -------
    sizes : dict
        Dictionary of (file, size) pairs.
    """
    files = {}
    for filename in os.listdir(dirname):
        path = os.path.join(dirname, filename)
        if os.path.isfile(path):
            files[filename] = os.stat(path).st_size
    return files
