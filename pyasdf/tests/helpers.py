# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os
import sys

import six

from ..asdf import AsdfFile, get_asdf_library_info
from ..conftest import RangeHTTPServer
from ..extension import _builtin_extension_list
from .. import util

from ..tags.core import AsdfObject


def assert_tree_match(old_tree, new_tree, funcname='assert_equal',
                      ignore_keys=None):
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

    ignore_keys : list of str
        List of keys to ignore
    """
    seen = set()

    if ignore_keys is None:
        ignore_keys = ['asdf_library', 'history']
    ignore_keys = set(ignore_keys)

    def recurse(old, new):
        if id(old) in seen or id(new) in seen:
            return
        seen.add(id(old))
        seen.add(id(new))

        old_type = _builtin_extension_list.type_index.from_custom_type(type(old))
        new_type = _builtin_extension_list.type_index.from_custom_type(type(new))

        if (old_type is not None and
            new_type is not None and
            old_type is new_type and
            hasattr(old_type, funcname)):
            getattr(old_type, funcname)(old, new)
        elif isinstance(old, dict) and isinstance(new, dict):
            assert (set(x for x in old.keys() if x not in ignore_keys) ==
                    set(x for x in new.keys() if x not in ignore_keys))
            for key in old.keys():
                if key not in ignore_keys:
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
        assert 'asdf_library' in ff.tree
        assert ff.tree['asdf_library'] == get_asdf_library_info()
        assert_tree_match(tree, ff.tree)
        if asdf_check_func:
            asdf_check_func(ff)

    buff.seek(0)
    ff = AsdfFile()
    content = AsdfFile._open_impl(ff, buff, _get_yaml_content=True)
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

    # Make sure everything works without a block index
    write_options['include_block_index'] = False
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

    # Now try everything on an HTTP range server
    if not sys.platform.startswith('win'):
        server = RangeHTTPServer()
        try:
            ff = AsdfFile(tree)
            ff.write_to(os.path.join(server.tmpdir, 'test.asdf'), **write_options)
            with AsdfFile.open(server.url + 'test.asdf', mode='r') as ff:
                assert_tree_match(tree, ff.tree)
                if asdf_check_func:
                    asdf_check_func(ff)
        finally:
            server.finalize()


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


def close_fits(hdulist):
    """
    Forcibly close all of the mmap'd HDUs in a FITS file.
    """
    for hdu in hdulist:
        if hdu.data is not None:
            base = util.get_array_base(hdu.data)
            if hasattr(base, 'flush'):
                base.flush()
                base._mmap.close()
