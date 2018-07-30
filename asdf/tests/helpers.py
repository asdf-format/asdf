# Licensed under a 3-clause BSD style license - see LICENSE.rst # -*- coding: utf-8 -*-

import io
import os
import sys

try:
    from astropy.coordinates import ICRS
except ImportError:
    ICRS = None

try:
    from astropy.coordinates.representation import CartesianRepresentation
except ImportError:
    CartesianRepresentation = None

try:
    from astropy.coordinates.representation import CartesianDifferential
except ImportError:
    CartesianDifferential = None

from ..asdf import AsdfFile, get_asdf_library_info
from .httpserver import RangeHTTPServer
from ..extension import default_extensions
from .. import util
from .. import versioning

from ..tags.core import AsdfObject

try:
    from pytest_remotedata.disable_internet import INTERNET_OFF
except ImportError:
    INTERNET_OFF = False


if sys.version_info >= (3, 7):
    from importlib import resources
else:
    try:
        import importlib_resources as resources
    except ImportError:
        resources = None


__all__ = ['get_test_data_path', 'assert_tree_match', 'assert_roundtrip_tree',
           'yaml_to_asdf', 'get_file_sizes', 'display_warnings']


def get_test_data_path(name, module=None):
    if resources is None:
        raise RuntimeError("The importlib_resources package is required to get"
                           " test data on systems with Python < 3.7")

    if module is None:
        from . import data as test_data
        module = test_data

    with resources.path(module, name) as path:
        return str(path)


def assert_tree_match(old_tree, new_tree, ctx=None,
                      funcname='assert_equal', ignore_keys=None):
    """
    Assert that two ASDF trees match.

    Parameters
    ----------
    old_tree : ASDF tree

    new_tree : ASDF tree

    ctx : ASDF file context
        Used to look up the set of types in effect.

    funcname : `str` or `callable`
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

    if ctx is None:
        version_string = str(versioning.default_version)
        ctx = default_extensions.extension_list
    else:
        version_string = ctx.version_string

    def recurse(old, new):
        if id(old) in seen or id(new) in seen:
            return
        seen.add(id(old))
        seen.add(id(new))

        old_type = ctx.type_index.from_custom_type(type(old), version_string)
        new_type = ctx.type_index.from_custom_type(type(new), version_string)

        if (old_type is not None and
            new_type is not None and
            old_type is new_type and
            (callable(funcname) or hasattr(old_type, funcname))):

            if callable(funcname):
                funcname(old, new)
            else:
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
        # The astropy classes CartesianRepresentation, CartesianDifferential,
        # and ICRS do not define equality in a way that is meaningful for unit
        # tests. We explicitly compare the fields that we care about in order
        # to enable our unit testing. It is possible that in the future it will
        # be necessary or useful to account for fields that are not currently
        # compared.
        elif CartesianRepresentation is not None and \
                isinstance(old, CartesianRepresentation):
            assert old.x == new.x and old.y == new.y and old.z == new.z
        elif CartesianDifferential is not None and \
                isinstance(old, CartesianDifferential):
            assert old.d_x == new.d_x and old.d_y == new.d_y and \
                old.d_z == new.d_z
        elif ICRS is not None and isinstance(old, ICRS):
            assert old.ra == new.ra and old.dec == new.dec
        else:
            assert old == new

    recurse(old_tree, new_tree)


def assert_roundtrip_tree(tree, tmpdir, *, asdf_check_func=None,
                          raw_yaml_check_func=None, write_options={}, extensions=None,
                          tree_match_func='assert_equal'):
    """
    Assert that a given tree saves to ASDF and, when loaded back,
    the tree matches the original tree.

    tree : ASDF tree

    tmpdir : str
        Path to temporary directory to save file

    tree_match_func : `str` or `callable`
        Passed to `assert_tree_match` and used to compare two objects in the
        tree.

    raw_yaml_check_func : callable, optional
        Will be called with the raw YAML content as a string to
        perform any additional checks.

    asdf_check_func : callable, optional
        Will be called with the reloaded ASDF file to perform any
        additional checks.
    """
    fname = str(tmpdir.join('test.asdf'))

    # First, test writing/reading a BytesIO buffer
    buff = io.BytesIO()
    AsdfFile(tree, extensions=extensions).write_to(buff, **write_options)
    assert not buff.closed
    buff.seek(0)
    with AsdfFile.open(buff, mode='rw', extensions=extensions) as ff:
        assert not buff.closed
        assert isinstance(ff.tree, AsdfObject)
        assert 'asdf_library' in ff.tree
        assert ff.tree['asdf_library'] == get_asdf_library_info()
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)

    buff.seek(0)
    ff = AsdfFile(extensions=extensions)
    content = AsdfFile._open_impl(ff, buff, _get_yaml_content=True)
    buff.close()
    # We *never* want to get any raw python objects out
    assert b'!!python' not in content
    assert b'!core/asdf' in content
    assert content.startswith(b'%YAML 1.1')
    if raw_yaml_check_func:
        raw_yaml_check_func(content)

    # Then, test writing/reading to a real file
    ff = AsdfFile(tree, extensions=extensions)
    ff.write_to(fname, **write_options)
    with AsdfFile.open(fname, mode='rw', extensions=extensions) as ff:
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)

    # Make sure everything works without a block index
    write_options['include_block_index'] = False
    buff = io.BytesIO()
    AsdfFile(tree, extensions=extensions).write_to(buff, **write_options)
    assert not buff.closed
    buff.seek(0)
    with AsdfFile.open(buff, mode='rw', extensions=extensions) as ff:
        assert not buff.closed
        assert isinstance(ff.tree, AsdfObject)
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)

    # Now try everything on an HTTP range server
    if not INTERNET_OFF and not sys.platform.startswith('win'):
        server = RangeHTTPServer()
        try:
            ff = AsdfFile(tree, extensions=extensions)
            ff.write_to(os.path.join(server.tmpdir, 'test.asdf'), **write_options)
            with AsdfFile.open(server.url + 'test.asdf', mode='r',
                               extensions=extensions) as ff:
                assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
                if asdf_check_func:
                    asdf_check_func(ff)
        finally:
            server.finalize()


def yaml_to_asdf(yaml_content, yaml_headers=True, standard_version=None):
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
    if isinstance(yaml_content, str):
        yaml_content = yaml_content.encode('utf-8')

    buff = io.BytesIO()

    if standard_version is None:
        standard_version = versioning.default_version

    if yaml_headers:
        buff.write("""#ASDF {0}
#ASDF_STANDARD {1}
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-{0}
""".format(AsdfObject.version, standard_version).encode('ascii'))
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


def display_warnings(_warnings):
    """
    Return a string that displays a list of unexpected warnings

    Parameters
    ----------
    _warnings : iterable
        List of warnings to be displayed

    Returns
    -------
    msg : str
        String containing the warning messages to be displayed
    """
    if len(_warnings) == 0:
        return "No warnings occurred (was one expected?)"

    msg = "Unexpected warning(s) occurred:\n"
    for warning in _warnings:
        msg += "{}:{}: {}: {}\n".format(
            warning.filename,
            warning.lineno,
            warning.category.__name__,
            warning.message)
    return msg
