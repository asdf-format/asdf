import copy
import getpass
import io
import os
import pathlib
import sys

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import asdf
from asdf import config_context, get_config, treeutil, versioning
from asdf.exceptions import AsdfPackageVersionWarning, ValidationError
from asdf.extension import ExtensionProxy
from asdf.resource import ResourceMappingProxy
from asdf.testing.helpers import roundtrip_object, yaml_to_asdf

from ._helpers import assert_tree_match

RNG = np.random.default_rng(97)


def test_get_data_from_closed_file(tmp_path):
    path = str(tmp_path / "test.asdf")

    my_array = np.arange(0, 64).reshape((8, 8))

    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path) as ff:
        pass

    with pytest.raises(IOError, match=r"Cannot access data from closed ASDF file"):
        assert_array_equal(my_array, ff.tree["my_array"])


def test_no_warning_nan_array(tmp_path):
    """
    Tests for a regression that was introduced by
    https://github.com/asdf-format/asdf/pull/557
    where saving an array with a nan resulted in a warning
    """
    roundtrip_object(np.array([1, 2, np.nan]))


@pytest.mark.skipif(
    not sys.platform.startswith("win") and getpass.getuser() == "root",
    reason="Cannot make file read-only if user is root",
)
def test_open_readonly(tmp_path):
    tmpfile = str(tmp_path / "readonly.asdf")

    tree = {"foo": 42, "bar": "hello", "baz": np.arange(20)}
    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, all_array_storage="internal")

    os.chmod(tmpfile, 0o440)
    assert os.access(tmpfile, os.W_OK) is False

    with asdf.open(tmpfile, memmap=True) as af:
        assert af["baz"].flags.writeable is False

    with pytest.raises(PermissionError, match=r".* Permission denied: .*"), asdf.open(tmpfile, mode="rw"):
        pass


def test_open_validate_on_read(tmp_path):
    content = """
invalid_software: !core/software-1.0.0
  name: Minesweeper
  version: 3
"""
    buff = yaml_to_asdf(content)

    get_config().validate_on_read = True
    with pytest.raises(ValidationError, match=r".* is not of type .*"), asdf.open(buff):
        pass

    buff.seek(0)

    get_config().validate_on_read = False
    with asdf.open(buff) as af:
        assert af["invalid_software"]["name"] == "Minesweeper"
        assert af["invalid_software"]["version"] == 3


def test_open_stream(tmp_path):
    file_path = tmp_path / "test.asdf"

    with asdf.AsdfFile() as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    class StreamWrapper:
        def __init__(self, fd):
            self._fd = fd

        def read(self, size=-1):
            return self._fd.read(size)

    with file_path.open("rb") as fd, asdf.open(StreamWrapper(fd)) as af:
        assert af["foo"] == "bar"


def test_atomic_write(tmp_path, small_tree):
    tmpfile = str(tmp_path / "test.asdf")

    ff = asdf.AsdfFile(small_tree)
    ff.write_to(tmpfile)

    with asdf.open(tmpfile, mode="r") as ff:
        ff.write_to(tmpfile)


def test_default_version():
    """
    See https://github.com/asdf-format/asdf/issues/364
    """
    ff = asdf.AsdfFile()
    assert ff.file_format_version == versioning._FILE_FORMAT_VERSION

    # make sure these are different AsdfVersion instances
    assert ff.file_format_version is not versioning._FILE_FORMAT_VERSION


def test_update_exceptions(tmp_path):
    path = str(tmp_path / "test.asdf")

    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with (
        asdf.open(path, mode="r", memmap=False) as ff,
        pytest.raises(
            IOError,
            match=r"Can not update, since associated file is read-only.*",
        ),
    ):
        ff.update()

    ff = asdf.AsdfFile(tree)
    buff = io.BytesIO()
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff, mode="rw") as ff:
        ff.update()

    with pytest.raises(ValueError, match=r"Can not update, since there is no associated file"):
        asdf.AsdfFile().update()


def test_top_level_tree(small_tree):
    tree = {"tree": small_tree}
    ff = asdf.AsdfFile(tree)
    assert_tree_match(ff.tree["tree"], ff["tree"])

    ff2 = asdf.AsdfFile()
    ff2["tree"] = small_tree
    assert_tree_match(ff2.tree["tree"], ff2["tree"])


def test_top_level_keys(small_tree):
    tree = {"tree": small_tree}
    ff = asdf.AsdfFile(tree)
    assert ff.tree.keys() == ff.keys()


def test_top_level_contains():
    tree = {
        "foo": 42,
        "bar": 43,
    }

    with asdf.AsdfFile(tree) as af:
        assert "foo" in af
        assert "bar" in af


def test_walk_and_modify_remove_keys():
    tree = {"foo": 42, "bar": 43}

    def func(x):
        if x == 42:
            return treeutil.RemoveNode
        return x

    tree2 = treeutil.walk_and_modify(tree, func)

    assert "foo" not in tree2
    assert "bar" in tree2


def test_walk_and_modify_retain_none():
    tree = {"foo": 42, "bar": None}

    def func(x):
        if x == 42:
            return None
        return x

    tree2 = treeutil.walk_and_modify(tree, func)

    assert tree2["foo"] is None
    assert tree2["bar"] is None


def test_copy(tmp_path):
    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array, "foo": {"bar": "baz"}}
    ff = asdf.AsdfFile(tree)
    ff.write_to(str(tmp_path / "test.asdf"))

    with asdf.open(str(tmp_path / "test.asdf")) as ff:
        ff2 = ff.copy()
        ff2.tree["my_array"] *= 2
        ff2.tree["foo"]["bar"] = "boo"

        assert np.all(ff2.tree["my_array"] == ff.tree["my_array"] * 2)
        assert ff.tree["foo"]["bar"] == "baz"

    assert_array_equal(ff2.tree["my_array"], ff2.tree["my_array"])


def test_access_tree_outside_handler(tmp_path):
    tempname = str(tmp_path / "test.asdf")

    tree = {"random": np.random.random(10)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(str(tempname))

    with asdf.open(tempname) as newf:
        pass

    # Accessing array data outside of handler should fail
    with pytest.raises(OSError, match=r"Cannot access data from closed ASDF file"):
        repr(newf.tree["random"])

    # Using the top-level getattr should also fail
    with pytest.raises(OSError, match=r"Cannot access data from closed ASDF file"):
        repr(newf["random"])


def test_context_handler_resolve_and_inline(tmp_path):
    """
    This reproduces the issue reported in
    https://github.com/asdf-format/asdf/issues/406
    """
    tempname = str(tmp_path / "test.asdf")

    tree = {"random": np.random.random(10)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(str(tempname))

    with asdf.open(tempname) as newf:
        newf.resolve_references()
        newf.set_array_storage(newf["random"], "inline")

    with pytest.raises(OSError, match=r"Cannot access data from closed ASDF file"):
        newf.tree["random"][0]


def test_open_pathlib_path(tmp_path):
    filename = str(tmp_path / "pathlib.asdf")
    path = pathlib.Path(filename)

    tree = {"data": np.ones(10)}

    with asdf.AsdfFile(tree) as af:
        af.write_to(path)

    with asdf.open(path) as af:
        assert (af["data"] == tree["data"]).all()


@pytest.mark.parametrize(
    ("installed", "extension", "warns"),
    [
        (None, "2.0.0", True),
        ("1.2.3", "2.0.0", True),
        ("1.2.3", "2.0.dev10842", True),
        ("2.0.0", "2.0.0", False),
        ("2.0.1", "2.0.0", False),
        ("2.0.1", "2.0.dev12345", False),
    ],
)
def test_extension_version_check(installed, extension, warns):
    class FooExtension:
        extension_uri = "asdf://somewhere.org/extensions/foo-1.0.0"

    proxy = ExtensionProxy(FooExtension(), package_name="foo", package_version=installed)

    with config_context() as config:
        if installed is not None:
            config.add_extension(proxy)
        af = asdf.AsdfFile()

    af._fname = "test.asdf"

    tree = {
        "history": {
            "extensions": [
                asdf.tags.core.ExtensionMetadata(
                    extension_uri=FooExtension.extension_uri,
                    software=asdf.tags.core.Software(name="foo", version=extension),
                ),
            ],
        },
    }

    if warns:
        with pytest.warns(AsdfPackageVersionWarning, match=r"File 'test.asdf' was created with"):
            af._check_extensions(tree)

        with pytest.raises(RuntimeError, match=r"^File 'test.asdf' was created with"):
            af._check_extensions(tree, strict=True)

    else:
        af._check_extensions(tree)


@pytest.mark.parametrize(
    ("installed", "extension", "warns"),
    [
        (None, "2.0.0", True),
        ("1.2.3", "2.0.0", True),
        ("1.2.3", "2.0.dev10842", True),
        ("2.0.0", "2.0.0", False),
        ("2.0.1", "2.0.0", False),
        ("2.0.1", "2.0.dev12345", False),
    ],
)
def test_check_extension_manifest_software(installed, extension, warns):
    class FooExtension:
        extension_uri = "asdf://somewhere.org/extensions/foo-1.0.0"

    proxy = ExtensionProxy(FooExtension(), package_name="foo", package_version="1.0.0")

    mapping = ResourceMappingProxy({}, package_name="bar", package_version=installed)

    with config_context() as config:
        config.add_extension(proxy)
        if installed is not None:
            config.add_resource_mapping(mapping)
        af = asdf.AsdfFile()

        af._fname = "test.asdf"

        tree = {
            "history": {
                "extensions": [
                    asdf.tags.core.ExtensionMetadata(
                        extension_uri=FooExtension.extension_uri,
                        software=asdf.tags.core.Software(name="foo", version="1.0.0"),
                        manifest_software=asdf.tags.core.Software(name="bar", version=extension),
                    ),
                ],
            },
        }

        if warns:
            with pytest.warns(AsdfPackageVersionWarning, match=r"File 'test.asdf' was created with"):
                af._check_extensions(tree)

            with pytest.raises(RuntimeError, match=r"^File 'test.asdf' was created with"):
                af._check_extensions(tree, strict=True)

        else:
            af._check_extensions(tree)


def test_extension_check_no_warning_on_builtin():
    """
    Prior to asdf 3.0 files were written using the asdf.extension.BuiltinExtension
    (which used the legacy extension api). This extension was removed in
    asdf 3.0. We don't want to warn that this extension is missing for every
    file that is opened so make sure _check_extensions doesn't warn
    that BuiltinExtension is missing.
    """
    af = asdf.AsdfFile()
    tree = {
        "history": {
            "extensions": [
                asdf.tags.core.ExtensionMetadata(
                    extension_class="asdf.extension.BuiltinExtension",
                    software=asdf.tags.core.Software(name="asdf", version="2.15.1"),
                ),
            ],
        },
    }
    af._check_extensions(tree)


@pytest.mark.parametrize(
    ("array_inline_threshold", "inline_blocks", "internal_blocks"),
    [
        (None, 0, 2),
        (10, 1, 1),
        (7, 1, 1),
        (5, 0, 2),
        (0, 0, 2),
        (1, 0, 2),
    ],
)
def test_array_inline_threshold(array_inline_threshold, inline_blocks, internal_blocks, tmp_path):
    file_path = tmp_path / "test.asdf"
    tree = {"small_array": np.arange(6), "large_array": np.arange(100)}

    with asdf.config_context() as config:
        config.array_inline_threshold = array_inline_threshold

        with asdf.AsdfFile(tree) as af:
            af.write_to(file_path)
        with asdf.open(file_path) as af:
            assert len(af._blocks.blocks) == internal_blocks


@pytest.mark.parametrize(
    ("array_inline_threshold", "inline_blocks", "internal_blocks"),
    [
        (None, 0, 2),
        (10, 2, 0),
        (5, 0, 2),
    ],
)
def test_array_inline_threshold_masked_array(array_inline_threshold, inline_blocks, internal_blocks, tmp_path):
    file_path = tmp_path / "test.asdf"
    arr = np.arange(6)
    masked_arr = np.ma.masked_equal(arr, 3)
    tree = {"masked_arr": masked_arr}

    with asdf.config_context() as config:
        config.array_inline_threshold = array_inline_threshold

        with asdf.AsdfFile(tree) as af:
            af.write_to(file_path)
        with asdf.open(file_path) as af:
            assert len(af._blocks.blocks) == internal_blocks


@pytest.mark.parametrize(
    ("array_inline_threshold", "inline_blocks", "internal_blocks"),
    [
        (None, 0, 1),
        (10, 1, 0),
        (5, 0, 1),
    ],
)
def test_array_inline_threshold_string_array(array_inline_threshold, inline_blocks, internal_blocks, tmp_path):
    file_path = tmp_path / "test.asdf"
    arr = np.array(["peach", "plum", "apricot", "nectarine", "cherry", "pluot"])
    tree = {"array": arr}

    with asdf.config_context() as config:
        config.array_inline_threshold = array_inline_threshold

        with asdf.AsdfFile(tree) as af:
            af.write_to(file_path)
        with asdf.open(file_path) as af:
            assert len(af._blocks.blocks) == internal_blocks


def test_history_entries(tmp_path):
    path = str(tmp_path / "test.asdf")
    message = "Twas brillig, and the slithy toves"

    af = asdf.AsdfFile()
    af.add_history_entry(message)
    af.write_to(path)
    with asdf.open(path) as af:
        assert af["history"]["entries"][0]["description"] == message

    af = asdf.AsdfFile()
    af.write_to(path)
    with asdf.open(path) as af:
        af.add_history_entry(message)
        assert af["history"]["entries"][0]["description"] == message


def test_array_access_after_file_close(tmp_path):
    path = str(tmp_path / "test.asdf")
    data = np.arange(10)
    asdf.AsdfFile({"data": data}).write_to(path)

    # Normally it's not possible to read the array after
    # the file has been closed:
    with asdf.open(path) as af:
        tree = af.tree
    with pytest.raises(OSError, match=r"ASDF file has already been closed. Can not get the data."):
        tree["data"][0]

    # With memory mapping disabled and copying arrays enabled,
    # the array data should still persist in memory after close:
    with asdf.open(path, lazy_load=False, memmap=False) as af:
        tree = af.tree
    assert_array_equal(tree["data"], data)


def test_none_values(tmp_path):
    path = str(tmp_path / "test.asdf")

    af = asdf.AsdfFile({"foo": None})
    af.write_to(path)
    with asdf.open(path) as af:
        assert "foo" in af
        assert af["foo"] is None


def test_asdf_standard_version_tag_selection():
    buff = io.BytesIO()

    af = asdf.AsdfFile()
    af.write_to(buff, version="1.0.0")
    buff.seek(0)
    content = buff.read()
    assert b"!core/asdf-1.0.0" in content
    assert b"!core/asdf-1.1.0" not in content

    buff.seek(0)
    af.write_to(buff, version="1.2.0")  # asdf-standard 1.2 uses asdf-object 1.1 tag
    buff.seek(0)
    content = buff.read()
    assert b"!core/asdf-1.0.0" not in content
    assert b"!core/asdf-1.1.0" in content


def test_update_asdf_standard_version_tag_selection():
    buff = io.BytesIO()

    af = asdf.AsdfFile()
    af.write_to(buff, version="1.0.0")

    buff.seek(0)
    with asdf.open(buff, mode="rw") as af:
        af.update(version="1.2.0")  # asdf-standard 1.2 uses asdf-object 1.1 tag
    buff.seek(0)
    content = buff.read()
    assert b"!core/asdf-1.1.0" in content
    assert b"!core/asdf-1.0.0" not in content


@pytest.mark.parametrize("valid_filename", [True, False], ids=["valid_filename", "invalid_filename"])
def test_write_to_no_tree_modification(tmp_path, valid_filename):
    if valid_filename:
        fn = tmp_path / "test.asdf"
    else:
        fn = "invalid/missing.asdf"
    fn2 = tmp_path / "test2.asdf"
    tree = {"foo": None}
    af = asdf.AsdfFile(tree.copy())
    try:
        af.write_to(fn)
    except Exception:
        if valid_filename:
            raise
    assert tree == af.tree
    if not valid_filename:
        return
    with asdf.open(fn) as af:
        af["history"]["extensions"][0]["software"]["version"] = "0.0.0.dev+abcdefg"
        af["asdf_library"]["author"] = "foo"
        tree = copy.deepcopy(af.tree)
        af.write_to(fn2)
        assert af.tree == tree


@pytest.mark.parametrize("valid_filename", [True, False], ids=["valid_filename", "invalid_filename"])
def test_write_to_no_version_modification(tmp_path, valid_filename):
    if valid_filename:
        fn = tmp_path / "test.asdf"
    else:
        fn = "invalid/missing.asdf"
    tree = {"foo": None}
    af = asdf.AsdfFile(tree.copy(), version="1.0.0")
    try:
        af.write_to(fn, version="1.1.0")
    except Exception:
        if valid_filename:
            raise
    assert af.version_string == "1.0.0"
    if not valid_filename:
        return
    with asdf.open(fn) as af:
        assert af.version_string == "1.1.0"
