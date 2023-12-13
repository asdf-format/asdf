import io
import os
import warnings
from pathlib import Path

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

import numpy as np

import asdf
from asdf._asdf import AsdfFile, _get_asdf_library_info
from asdf.exceptions import AsdfConversionWarning
from asdf.tags.core import AsdfObject

from .httpserver import RangeHTTPServer

try:
    from pytest_remotedata.disable_internet import INTERNET_OFF
except ImportError:
    INTERNET_OFF = False


__all__ = [
    "get_test_data_path",
    "assert_tree_match",
    "assert_roundtrip_tree",
]


def get_test_data_path(name, module=None):
    if module is None:
        from . import data as test_data

        module = test_data

    module_root = Path(module.__file__).parent

    if name is None or name == "":
        return str(module_root)

    return str(module_root / name)


def assert_tree_match(old_tree, new_tree, ctx=None, funcname="assert_equal", ignore_keys=None):
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
        ``assert_equal`` handles Numpy arrays.

    ignore_keys : list of str
        List of keys to ignore
    """
    seen = set()

    if ignore_keys is None:
        ignore_keys = ["asdf_library", "history"]
    ignore_keys = set(ignore_keys)

    def recurse(old, new):
        if id(old) in seen or id(new) in seen:
            return
        seen.add(id(old))
        seen.add(id(new))

        old_type = None
        new_type = None

        if (
            old_type is not None
            and new_type is not None
            and old_type is new_type
            and (callable(funcname) or hasattr(old_type, funcname))
        ):
            if callable(funcname):
                funcname(old, new)
            else:
                getattr(old_type, funcname)(old, new)

        elif isinstance(old, dict) and isinstance(new, dict):
            assert {x for x in old if x not in ignore_keys} == {x for x in new if x not in ignore_keys}
            for key in old:
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
        elif CartesianRepresentation is not None and isinstance(old, CartesianRepresentation):
            assert old.x == new.x
            assert old.y == new.y
            assert old.z == new.z
        elif CartesianDifferential is not None and isinstance(old, CartesianDifferential):
            assert old.d_x == new.d_x
            assert old.d_y == new.d_y
            assert old.d_z == new.d_z
        elif ICRS is not None and isinstance(old, ICRS):
            assert old.ra == new.ra
            assert old.dec == new.dec
        elif all([isinstance(obj, (np.ndarray, asdf.tags.core.NDArrayType)) for obj in (old, new)]):
            with warnings.catch_warnings():
                # The oldest deps job tests against versions of numpy where this
                # testing function raised a FutureWarning but still functioned
                # as expected
                warnings.filterwarnings("ignore", category=FutureWarning)
                if old.dtype.fields:
                    if not new.dtype.fields:
                        msg = "arrays not equal"
                        raise AssertionError(msg)
                    for f in old.dtype.fields:
                        np.testing.assert_array_equal(old[f], new[f])
                else:
                    np.testing.assert_array_equal(old.__array__(), new.__array__())
        else:
            assert old == new

    recurse(old_tree, new_tree)


def assert_roundtrip_tree(*args, **kwargs):
    """
    Assert that a given tree saves to ASDF and, when loaded back,
    the tree matches the original tree.

    tree : ASDF tree

    tmp_path : `str` or `pathlib.Path`
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
    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=AsdfConversionWarning)
        _assert_roundtrip_tree(*args, **kwargs)


def _assert_roundtrip_tree(
    tree,
    tmp_path,
    *,
    asdf_check_func=None,
    raw_yaml_check_func=None,
    write_options=None,
    init_options=None,
    extensions=None,
    tree_match_func="assert_equal",
):
    write_options = {} if write_options is None else write_options
    init_options = {} if init_options is None else init_options

    fname = os.path.join(str(tmp_path), "test.asdf")

    # First, test writing/reading a BytesIO buffer
    buff = io.BytesIO()
    AsdfFile(tree, extensions=extensions, **init_options).write_to(buff, **write_options)
    assert not buff.closed
    buff.seek(0)
    with asdf.open(buff, mode="rw", extensions=extensions) as ff:
        assert not buff.closed
        assert isinstance(ff.tree, AsdfObject)
        assert "asdf_library" in ff.tree
        assert ff.tree["asdf_library"] == _get_asdf_library_info()
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)

    buff.seek(0)
    ff = AsdfFile(extensions=extensions, **init_options)
    content = AsdfFile._open_impl(ff, buff, mode="r", _get_yaml_content=True)
    buff.close()
    # We *never* want to get any raw python objects out
    assert b"!!python" not in content
    assert b"!core/asdf" in content
    assert content.startswith(b"%YAML 1.1")
    if raw_yaml_check_func:
        raw_yaml_check_func(content)

    # Then, test writing/reading to a real file
    ff = AsdfFile(tree, extensions=extensions, **init_options)
    ff.write_to(fname, **write_options)
    with asdf.open(fname, mode="rw", extensions=extensions) as ff:
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)

    # Make sure everything works without a block index
    write_options["include_block_index"] = False
    buff = io.BytesIO()
    AsdfFile(tree, extensions=extensions, **init_options).write_to(buff, **write_options)
    assert not buff.closed
    buff.seek(0)
    with asdf.open(buff, mode="rw", extensions=extensions) as ff:
        assert not buff.closed
        assert isinstance(ff.tree, AsdfObject)
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)

    # Now try everything on an HTTP range server
    if not INTERNET_OFF:
        server = RangeHTTPServer()
        try:
            ff = AsdfFile(tree, extensions=extensions, **init_options)
            ff.write_to(os.path.join(server.tmpdir, "test.asdf"), **write_options)
            with asdf.open(server.url + "test.asdf", mode="r", extensions=extensions) as ff:
                assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
                if asdf_check_func:
                    asdf_check_func(ff)
        finally:
            server.finalize()

    # Now don't be lazy and check that nothing breaks
    with io.BytesIO() as buff:
        AsdfFile(tree, extensions=extensions, **init_options).write_to(buff, **write_options)
        buff.seek(0)
        ff = asdf.open(buff, extensions=extensions, memmap=False, lazy_load=False)
        # Ensure that all the blocks are loaded
        for block in ff._blocks.blocks:
            assert block._data is not None and not callable(block._data)
    # The underlying file is closed at this time and everything should still work
    assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
    if asdf_check_func:
        asdf_check_func(ff)

    # Now repeat with memmap=True and a real file to test mmap()
    AsdfFile(tree, extensions=extensions, **init_options).write_to(fname, **write_options)
    with asdf.open(fname, mode="rw", extensions=extensions, memmap=True, lazy_load=False) as ff:
        for block in ff._blocks.blocks:
            assert block._data is not None and not callable(block._data)
        assert_tree_match(tree, ff.tree, ff, funcname=tree_match_func)
        if asdf_check_func:
            asdf_check_func(ff)
