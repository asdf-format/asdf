# -*- coding: utf-8 -*-

import os
import io
import pathlib

import numpy as np
from numpy.testing import assert_array_equal
from astropy.modeling import models

import pytest

from jsonschema.exceptions import ValidationError

import asdf
from asdf import treeutil
from asdf import extension
from asdf import resolver
from asdf import schema
from asdf import versioning
from asdf.exceptions import AsdfDeprecationWarning
from .helpers import assert_tree_match, assert_roundtrip_tree, display_warnings, yaml_to_asdf


def test_get_data_from_closed_file(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    my_array = np.arange(0, 64).reshape((8, 8))

    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path) as ff:
        pass

    with pytest.raises(IOError):
        assert_array_equal(my_array, ff.tree['my_array'])


def test_no_warning_nan_array(tmpdir):
    """
    Tests for a regression that was introduced by
    https://github.com/spacetelescope/asdf/pull/557
    """

    tree = dict(array=np.array([1, 2, np.nan]))

    with pytest.warns(None) as w:
        assert_roundtrip_tree(tree, tmpdir)
        assert len(w) == 0, display_warnings(w)


def test_warning_deprecated_open(tmpdir):

    tmpfile = str(tmpdir.join('foo.asdf'))

    tree = dict(foo=42, bar='hello')
    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile)

    with pytest.warns(AsdfDeprecationWarning):
        with asdf.AsdfFile.open(tmpfile) as af:
            assert_tree_match(tree, af.tree)


def test_open_readonly(tmpdir):

    tmpfile = str(tmpdir.join('readonly.asdf'))

    tree = dict(foo=42, bar='hello', baz=np.arange(20))
    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, all_array_storage='internal')

    os.chmod(tmpfile, 0o440)
    assert os.access(tmpfile, os.W_OK) == False

    with asdf.open(tmpfile) as af:
        assert af['baz'].flags.writeable == False

    with pytest.raises(PermissionError):
        with asdf.open(tmpfile, mode='rw'):
            pass


def test_open_validate_on_read(tmpdir):
    content = """
invalid_software: !core/software-1.0.0
  name: Minesweeper
  version: 3
"""
    buff = yaml_to_asdf(content)

    with pytest.raises(ValidationError):
        with asdf.open(buff, validate_on_read=True):
            pass

    buff.seek(0)

    with asdf.open(buff, validate_on_read=False) as af:
        assert af["invalid_software"]["name"] == "Minesweeper"
        assert af["invalid_software"]["version"] == 3


def test_atomic_write(tmpdir, small_tree):
    tmpfile = os.path.join(str(tmpdir), 'test.asdf')

    ff = asdf.AsdfFile(small_tree)
    ff.write_to(tmpfile)

    with asdf.open(tmpfile, mode='r') as ff:
        ff.write_to(tmpfile)


def test_overwrite(tmpdir):
    # This is intended to reproduce the following issue:
    # https://github.com/spacetelescope/asdf/issues/100
    tmpfile = os.path.join(str(tmpdir), 'test.asdf')
    aff = models.AffineTransformation2D(matrix=[[1, 2], [3, 4]])
    f = asdf.AsdfFile()
    f.tree['model'] = aff
    f.write_to(tmpfile)
    model = f.tree['model']

    ff = asdf.AsdfFile()
    ff.tree['model'] = model
    ff.write_to(tmpfile)


def test_default_version():
    # See https://github.com/spacetelescope/asdf/issues/364

    version_map = versioning.get_version_map(versioning.default_version)

    ff = asdf.AsdfFile()
    assert ff.file_format_version == version_map['FILE_FORMAT']


def test_update_exceptions(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path, mode='r', copy_arrays=True) as ff:
        with pytest.raises(IOError):
            ff.update()

    ff = asdf.AsdfFile(tree)
    buff = io.BytesIO()
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff, mode='rw') as ff:
        ff.update()

    with pytest.raises(ValueError):
        asdf.AsdfFile().update()


def test_top_level_tree(small_tree):
    tree = {'tree': small_tree}
    ff = asdf.AsdfFile(tree)
    assert_tree_match(ff.tree['tree'], ff['tree'])

    ff2 = asdf.AsdfFile()
    ff2['tree'] = small_tree
    assert_tree_match(ff2.tree['tree'], ff2['tree'])


def test_top_level_keys(small_tree):
    tree = {'tree': small_tree}
    ff = asdf.AsdfFile(tree)
    assert ff.tree.keys() == ff.keys()


def test_top_level_contains():
    tree = {
        'foo': 42,
        'bar': 43,
    }

    with asdf.AsdfFile(tree) as af:
        assert 'foo' in af
        assert 'bar' in af


def test_walk_and_modify_remove_keys():
    tree = {
        'foo': 42,
        'bar': 43
    }

    def func(x):
        if x == 42:
            return None
        return x

    tree2 = treeutil.walk_and_modify(tree, func)

    assert 'foo' not in tree2
    assert 'bar' in tree2


def test_copy(tmpdir):
    tmpdir = str(tmpdir)

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array, 'foo': {'bar': 'baz'}}
    ff = asdf.AsdfFile(tree)
    ff.write_to(os.path.join(tmpdir, 'test.asdf'))

    with asdf.open(os.path.join(tmpdir, 'test.asdf')) as ff:
        ff2 = ff.copy()
        ff2.tree['my_array'] *= 2
        ff2.tree['foo']['bar'] = 'boo'

        assert np.all(ff2.tree['my_array'] ==
                      ff.tree['my_array'] * 2)
        assert ff.tree['foo']['bar'] == 'baz'

    assert_array_equal(ff2.tree['my_array'], ff2.tree['my_array'])


def test_tag_to_schema_resolver_deprecation():
    ff = asdf.AsdfFile()
    with pytest.warns(AsdfDeprecationWarning):
        ff.tag_to_schema_resolver('foo')

    with pytest.warns(AsdfDeprecationWarning):
        extension_list = extension.default_extensions.extension_list
        extension_list.tag_to_schema_resolver('foo')


def test_access_tree_outside_handler(tmpdir):
    tempname = str(tmpdir.join('test.asdf'))

    tree = {'random': np.random.random(10)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(str(tempname))

    with asdf.open(tempname) as newf:
        pass

    # Accessing array data outside of handler should fail
    with pytest.raises(OSError):
        repr(newf.tree['random'])

    # Using the top-level getattr should also fail
    with pytest.raises(OSError):
        repr(newf['random'])


def test_context_handler_resolve_and_inline(tmpdir):
    # This reproduces the issue reported in
    # https://github.com/spacetelescope/asdf/issues/406
    tempname = str(tmpdir.join('test.asdf'))

    tree = {'random': np.random.random(10)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(str(tempname))

    with asdf.open(tempname) as newf:
        newf.resolve_and_inline()

    with pytest.raises(OSError):
        newf.tree['random'][0]


def test_open_pathlib_path(tmpdir):

    filename = str(tmpdir.join('pathlib.asdf'))
    path = pathlib.Path(filename)

    tree = {'data': np.ones(10)}

    with asdf.AsdfFile(tree) as af:
        af.write_to(path)

    with asdf.open(path) as af:
        assert (af['data'] == tree['data']).all()


@pytest.mark.parametrize('installed,extension,warns', [
    ('1.2.3', '2.0.0', True),
    ('1.2.3', '2.0.dev10842', True),
    ('2.0.0', '2.0.0', False),
    ('2.0.1', '2.0.0', False),
    ('2.0.1', '2.0.dev12345', False),
])
def test_extension_version_check(installed, extension, warns):

    af = asdf.AsdfFile()
    af._fname = 'test.asdf'
    af._extension_metadata['foo.extension.FooExtension'] = ('foo', installed)

    tree = {
        'history': {
            'extensions': [
                asdf.tags.core.ExtensionMetadata('foo.extension.FooExtension',
                    asdf.tags.core.Software(name='foo', version=extension)),
            ]
        }
    }

    if warns:
        with pytest.warns(UserWarning) as w:
            af._check_extensions(tree)
        assert str(w[0].message).startswith("File 'test.asdf' was created with")

        with pytest.raises(RuntimeError) as err:
            af._check_extensions(tree, strict=True)
        err.match("^File 'test.asdf' was created with")
    else:
        af._check_extensions(tree)


@pytest.mark.xfail(reason='Setting auto_inline option modifies AsdfFile state')
def test_auto_inline(tmpdir):

    outfile = str(tmpdir.join('test.asdf'))
    tree = dict(data=np.arange(6))

    # Use the same object for each write in order to make sure that there
    # aren't unanticipated side effects
    with asdf.AsdfFile(tree) as af:
        af.write_to(outfile)
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 1

        af.write_to(outfile, auto_inline=10)
        assert len(list(af.blocks.inline_blocks)) == 1
        assert len(list(af.blocks.internal_blocks)) == 0

        af.write_to(outfile)
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 1

        af.write_to(outfile, auto_inline=7)
        assert len(list(af.blocks.inline_blocks)) == 1
        assert len(list(af.blocks.internal_blocks)) == 0

        af.write_to(outfile, auto_inline=5)
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 1


@pytest.mark.skip(reason='Until inline_threshold is added as a write option')
def test_inline_threshold(tmpdir):

    tree = {
        'small': np.ones(10),
        'large': np.ones(100)
    }

    with asdf.AsdfFile(tree) as af:
        assert len(list(af.blocks.inline_blocks)) == 1
        assert len(list(af.blocks.internal_blocks)) == 1

    with asdf.AsdfFile(tree, inline_threshold=10) as af:
        assert len(list(af.blocks.inline_blocks)) == 1
        assert len(list(af.blocks.internal_blocks)) == 1

    with asdf.AsdfFile(tree, inline_threshold=5) as af:
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 2

    with asdf.AsdfFile(tree, inline_threshold=100) as af:
        assert len(list(af.blocks.inline_blocks)) == 2
        assert len(list(af.blocks.internal_blocks)) == 0


@pytest.mark.skip(reason='Until inline_threshold is added as a write option')
def test_inline_threshold_masked(tmpdir):

    mask = np.random.randint(0, 1+1, 20)
    masked_array = np.ma.masked_array(np.ones(20), mask=mask)

    tree = {
        'masked': masked_array
    }

    # Make sure that masked arrays aren't automatically inlined, even if they
    # are small enough
    with asdf.AsdfFile(tree) as af:
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 2

    tree = {
        'masked': masked_array,
        'normal': np.random.random(20)
    }

    with asdf.AsdfFile(tree) as af:
        assert len(list(af.blocks.inline_blocks)) == 1
        assert len(list(af.blocks.internal_blocks)) == 2


@pytest.mark.skip(reason='Until inline_threshold is added as a write option')
def test_inline_threshold_override(tmpdir):

    tmpfile = str(tmpdir.join('inline.asdf'))

    tree = {
        'small': np.ones(10),
        'large': np.ones(100)
    }

    with asdf.AsdfFile(tree) as af:
        af.set_array_storage(tree['small'], 'internal')
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 2

    with asdf.AsdfFile(tree) as af:
        af.set_array_storage(tree['large'], 'inline')
        assert len(list(af.blocks.inline_blocks)) == 2
        assert len(list(af.blocks.internal_blocks)) == 0

    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, all_array_storage='internal')
        assert len(list(af.blocks.inline_blocks)) == 0
        assert len(list(af.blocks.internal_blocks)) == 2

    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, all_array_storage='inline')
        assert len(list(af.blocks.inline_blocks)) == 2
        assert len(list(af.blocks.internal_blocks)) == 0


def test_resolver_deprecations():
    for resolver_method in [
        resolver.default_resolver,
        resolver.default_tag_to_url_mapping,
        resolver.default_url_mapping,
        schema.default_ext_resolver
    ]:
        with pytest.warns(AsdfDeprecationWarning):
            resolver_method("foo")


def test_get_default_resolver():
    resolver = extension.get_default_resolver()

    result = resolver('tag:stsci.edu:asdf/core/ndarray-1.0.0')

    assert result.endswith("/schemas/stsci.edu/asdf/core/ndarray-1.0.0.yaml")


def test_info_module(capsys, tmpdir):
    tree = dict(
        foo=42, bar="hello", baz=np.arange(20),
        nested={"woo": "hoo", "yee": "haw"},
        long_line="a" * 100
    )
    af = asdf.AsdfFile(tree)

    def _assert_correct_info(node_or_path):
        asdf.info(node_or_path)
        captured = capsys.readouterr()
        assert "foo" in captured.out
        assert "bar" in captured.out
        assert "baz" in captured.out

    _assert_correct_info(af)
    _assert_correct_info(af.tree)

    tmpfile = str(tmpdir.join("written.asdf"))
    af.write_to(tmpfile)
    af.close()

    _assert_correct_info(tmpfile)
    _assert_correct_info(pathlib.Path(tmpfile))

    for i in range(1, 10):
        asdf.info(af, max_rows=i)
        lines = capsys.readouterr().out.strip().split("\n")
        assert len(lines) <= i

    asdf.info(af, max_cols=80)
    assert "(truncated)" in capsys.readouterr().out
    asdf.info(af, max_cols=None)
    captured = capsys.readouterr().out
    assert "(truncated)" not in captured
    assert "a" * 100 in captured

    asdf.info(af, show_values=True)
    assert "hello" in capsys.readouterr().out
    asdf.info(af, show_values=False)
    assert "hello" not in capsys.readouterr().out

    tree = {
        "foo": ["alpha", "bravo", "charlie", "delta", "eagle"]
    }
    af = asdf.AsdfFile(tree)
    asdf.info(af, max_rows=(None,))
    assert "alpha" not in capsys.readouterr().out
    for i in range(1, 5):
        asdf.info(af, max_rows=(None, i))
        captured = capsys.readouterr()
        for val in tree["foo"][0:i-1]:
            assert val in captured.out
        for val in tree["foo"][i-1:]:
            assert val not in captured.out

def test_info_asdf_file(capsys, tmpdir):
    tree = dict(
        foo=42, bar="hello", baz=np.arange(20),
        nested={"woo": "hoo", "yee": "haw"},
        long_line="a" * 100
    )
    af = asdf.AsdfFile(tree)
    af.info()
    captured = capsys.readouterr()
    assert "foo" in captured.out
    assert "bar" in captured.out
    assert "baz" in captured.out


def test_search():
    tree = dict(foo=42, bar="hello", baz=np.arange(20))
    af = asdf.AsdfFile(tree)

    result = af.search("foo")
    assert result.node == 42

    result = af.search(type="ndarray")
    assert (result.node == tree["baz"]).all()

    result = af.search(value="hello")
    assert result.node == "hello"


def test_history_entries(tmpdir):
    path = str(tmpdir.join("test.asdf"))
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
