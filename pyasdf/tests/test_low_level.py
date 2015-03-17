# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import io
import os

from astropy.extern import six
from astropy.tests.helper import pytest

import numpy as np
from numpy.testing import assert_array_equal

from .. import asdf
from .. import constants
from .. import generic_io


def _get_small_tree():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2],
        'not_shared': np.arange(10, 0, -1, dtype=np.uint8)
        }
    return tree


def test_no_yaml_end_marker(tmpdir):
    content = b"""#ASDF 0.1.0
%YAML 1.2
%TAG ! tag:stsci.edu:asdf/0.1.0/
--- !core/asdf
foo: bar...baz
baz: 42
    """
    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        asdf.AsdfFile.read(buff)

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    with pytest.raises(ValueError):
        asdf.AsdfFile.read(fd)

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            asdf.AsdfFile.read(fd)


def test_no_final_newline(tmpdir):
    content = b"""#ASDF 0.1.0
%YAML 1.2
%TAG ! tag:stsci.edu:asdf/0.1.0/
--- !core/asdf
foo: ...bar...
baz: 42
..."""
    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with asdf.AsdfFile.read(buff) as ff:
        assert len(ff.tree) == 2

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    with asdf.AsdfFile.read(fd) as ff:
        assert len(ff.tree) == 2

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with asdf.AsdfFile.read(fd) as ff:
            assert len(ff.tree) == 2


def test_no_asdf_header(tmpdir):
    content = b"What? This ain't no ASDF file"

    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        asdf.AsdfFile.read(buff)

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            asdf.AsdfFile.read(fd)


def test_no_asdf_blocks(tmpdir):
    content = b"""#ASDF 0.1.0
%YAML 1.2
%TAG ! tag:stsci.edu:asdf/0.1.0/
--- !core/asdf
foo: bar
...
XXXXXXXX
    """

    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    ff = asdf.AsdfFile.read(buff)
    assert len(ff.blocks) == 0

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    ff = asdf.AsdfFile.read(fd)
    assert len(ff.blocks) == 0

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        ff = asdf.AsdfFile.read(fd)
    assert len(ff.blocks) == 0


def test_invalid_source():
    buff = io.BytesIO()

    ff = asdf.AsdfFile(_get_small_tree())
    ff.write_to(buff)

    buff.seek(0)
    ff2 = asdf.AsdfFile.read(buff)

    ff2.blocks.get_block(0)

    with pytest.raises(ValueError):
        ff2.blocks.get_block(2)

    with pytest.raises(IOError):
        ff2.blocks.get_block("http://127.0.0.1/")

    with pytest.raises(TypeError):
        ff2.blocks.get_block(42.0)

    with pytest.raises(ValueError):
        ff2.blocks.get_source(42.0)

    block = ff2.blocks.get_block(0)
    assert ff2.blocks.get_source(block) == 0


def test_empty_file():
    buff = io.BytesIO(b"#ASDF 0.1.0\n")
    buff.seek(0)

    ff = asdf.AsdfFile.read(buff)

    assert ff.tree == {}
    assert len(ff.blocks) == 0


def test_not_asdf_file():
    buff = io.BytesIO(b"SIMPLE")
    buff.seek(0)

    with pytest.raises(ValueError):
        asdf.AsdfFile.read(buff)

    buff = io.BytesIO(b"SIMPLE\n")
    buff.seek(0)

    with pytest.raises(ValueError):
        asdf.AsdfFile.read(buff)


def test_junk_file():
    buff = io.BytesIO(b"#ASDF 0.1.0\nFOO")
    buff.seek(0)

    with pytest.raises(IOError):
        asdf.AsdfFile.read(buff)


def test_block_mismatch():
    # This is a file with a single small block, followed by something
    # that has an invalid block magic number.

    buff = io.BytesIO(
        b'#ASDF 0.1.0\n\xd3BLK\x00\x28\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0FOOBAR')

    buff.seek(0)
    with pytest.raises(ValueError):
        asdf.AsdfFile.read(buff)


def test_block_header_too_small():
    # The block header size must be at least 40

    buff = io.BytesIO(
        b'#ASDF 0.1.0\n\xd3BLK\0\0')

    buff.seek(0)
    with pytest.raises(ValueError):
        asdf.AsdfFile.read(buff)


if six.PY2:
    def test_file_already_closed(tmpdir):
        # Test that referencing specific blocks in another asdf file
        # works.
        tree = _get_small_tree()

        path = os.path.join(str(tmpdir), 'test.asdf')
        ff = asdf.AsdfFile(tree)
        ff.write_to(path)

        with open(path, 'rb') as fd:
            ff2 = asdf.AsdfFile.read(fd)

        with pytest.raises(IOError):
            str(ff2.tree['science_data'][:])


def test_external_block(tmpdir):
    tmpdir = str(tmpdir)

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(my_array, 'external')
    assert ff.get_array_storage(my_array) == 'external'

    with ff.write_to(os.path.join(tmpdir, "test.asdf")):
        pass

    assert 'test0000.asdf' in os.listdir(tmpdir)


def test_external_block_non_url():
    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(my_array, 'external')
    assert ff.get_array_storage(my_array) == 'external'

    buff = io.BytesIO()
    with pytest.raises(ValueError):
        with ff.write_to(buff):
            pass


def test_invalid_array_storage():
    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    with pytest.raises(ValueError):
        ff.set_array_storage(my_array, 'foo')


def test_transfer_array_sources(tmpdir):
    tmpdir = str(tmpdir)

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    with ff.write_to(os.path.join(tmpdir, "test.asdf")):
        pass

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        original_fd = ff._fd
        assert_array_equal(my_array, ff.tree['my_array'])
        ff.write_to(os.path.join(tmpdir, "test2.asdf"))
        # Assert that the original file is closed
        assert original_fd._fd.closed

        # ...but when we access the data it is magically opened from
        # the new file.
        assert_array_equal(my_array, ff.tree['my_array'])

    assert ff._fd is None


def test_write_to_same(tmpdir):
    tmpdir = str(tmpdir)

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    ff = asdf.AsdfFile(tree)
    with ff.write_to(os.path.join(tmpdir, "test.asdf")):
        pass

    with asdf.AsdfFile.read(
            os.path.join(tmpdir, "test.asdf"), mode='rw') as ff:
        assert_array_equal(my_array, ff.tree['my_array'])
        ff.tree['extra'] = [0] * 1000
        ff.write_to(os.path.join(tmpdir, "test2.asdf"))

    with asdf.AsdfFile.read(
            os.path.join(tmpdir, "test2.asdf"), mode='rw') as ff:
        assert_array_equal(my_array, ff.tree['my_array'])


def test_pad_blocks(tmpdir):
    tmpdir = str(tmpdir)

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((8, 8)) * 1
    my_array2 = np.ones((42, 5)) * 2
    tree = {
        'my_array': my_array,
        'my_array2': my_array2
    }

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(os.path.join(tmpdir, "test.asdf"), pad_blocks=True)

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['my_array'], my_array)
        assert_array_equal(ff.tree['my_array2'], my_array2)


def test_update_expand_tree(tmpdir):
    tmpdir = str(tmpdir)

    # This is the case where the new tree can't fit in the available space
    my_array = np.arange(64) * 1
    my_array2 = np.arange(64) * 2
    tree = {
        'my_array': my_array,
        'my_array2': my_array2,
        'my_array3': np.arange(3)
    }

    with asdf.AsdfFile(tree) as ff:
        ff.blocks[tree['my_array3']].array_storage = 'inline'
        ff.write_to(os.path.join(tmpdir, "test.asdf"), pad_blocks=True)
        orig_offset = ff.blocks[ff.tree['my_array']].offset
        orig_offset2 = ff.blocks[ff.tree['my_array2']].offset
        ff.tree['extra'] = [0] * 6000
        ff.update()

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert orig_offset != ff.blocks[ff.tree['my_array']].offset
        assert orig_offset2 != ff.blocks[ff.tree['my_array2']].offset
        assert ff.blocks[ff.tree['my_array3']].array_storage == 'inline'
        assert_array_equal(ff.tree['my_array'], my_array)
        assert_array_equal(ff.tree['my_array2'], my_array2)

    # Now, we expand the header only by a little bit
    with asdf.AsdfFile(tree) as ff:
        ff.blocks[tree['my_array3']].array_storage = 'inline'
        ff.write_to(os.path.join(tmpdir, "test.asdf"), pad_blocks=True)
        orig_offset = ff.blocks[ff.tree['my_array']].offset
        ff.tree['extra'] = [0] * 2
        ff.update()

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert orig_offset == ff.blocks[ff.tree['my_array']].offset
        assert ff.blocks[ff.tree['my_array3']].array_storage == 'inline'
        assert_array_equal(ff.tree['my_array'], my_array)
        assert_array_equal(ff.tree['my_array2'], my_array2)


def _get_update_tree():
    return {
        'arrays': [
            np.arange(64) * 1,
            np.arange(64) * 2,
            np.arange(64) * 3
        ]
    }


def test_update_delete_first_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        del ff.tree['arrays'][0]
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][1])
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][2])


def test_update_delete_last_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        del ff.tree['arrays'][-1]
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][0])
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][1])


def test_update_delete_middle_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        del ff.tree['arrays'][1]
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][0])
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][2])


def test_update_replace_first_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        ff.tree['arrays'][0] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], np.arange(32))
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][1])
        assert_array_equal(ff.tree['arrays'][2], tree['arrays'][2])


def test_update_replace_last_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        ff.tree['arrays'][2] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][0])
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][1])
        assert_array_equal(ff.tree['arrays'][2], np.arange(32))


def test_update_replace_middle_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        ff.tree['arrays'][1] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][0])
        assert_array_equal(ff.tree['arrays'][1], np.arange(32))
        assert_array_equal(ff.tree['arrays'][2], tree['arrays'][2])


def test_update_add_array(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        ff.tree['arrays'].append(np.arange(32))
        ff.update()

    assert os.stat(path).st_size == original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][0])
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][1])
        assert_array_equal(ff.tree['arrays'][2], tree['arrays'][2])
        assert_array_equal(ff.tree['arrays'][3], np.arange(32))


def test_update_add_array_at_end(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf"), mode="rw") as ff:
        ff.tree['arrays'].append(np.arange(2048))
        ff.update()

    assert os.stat(path).st_size > original_size

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['arrays'][0], tree['arrays'][0])
        assert_array_equal(ff.tree['arrays'][1], tree['arrays'][1])
        assert_array_equal(ff.tree['arrays'][2], tree['arrays'][2])
        assert_array_equal(ff.tree['arrays'][3], np.arange(2048))
        print([x.offset for x in ff.blocks._blocks])


def test_update_replace_all_arrays(tmpdir):
    tmpdir = str(tmpdir)

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((64, 64)) * 1
    tree = {
        'my_array': my_array,
    }

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(os.path.join(tmpdir, "test.asdf"), pad_blocks=True)
        ff.tree['my_array'] = np.ones((64, 64)) * 2
        ff.update()

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['my_array'], np.ones((64, 64)) * 2)


def test_update_array_in_place(tmpdir):
    tmpdir = str(tmpdir)

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((64, 64)) * 1
    tree = {
        'my_array': my_array,
    }

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(os.path.join(tmpdir, "test.asdf"), pad_blocks=True)
        ff.tree['my_array'] *= 2
        ff.update()

    with asdf.AsdfFile.read(os.path.join(tmpdir, "test.asdf")) as ff:
        assert_array_equal(ff.tree['my_array'], np.ones((64, 64)) * 2)


def test_init_from_asdffile(tmpdir):
    tmpdir = str(tmpdir)

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    with asdf.AsdfFile(tree) as ff:
        ff2 = asdf.AsdfFile(ff)
        assert ff.tree['my_array'] is ff2.tree['my_array']
        assert_array_equal(ff.tree['my_array'], ff2.tree['my_array'])
        assert ff.blocks[my_array] != ff2.blocks[my_array]

        ff2.tree['my_array'] = None
        assert_array_equal(ff.tree['my_array'], my_array)

        ff.write_to(os.path.join(tmpdir, 'test.asdf'))

    with asdf.AsdfFile().read(os.path.join(tmpdir, 'test.asdf')) as ff:
        ff2 = asdf.AsdfFile(ff)
        assert not ff.tree['my_array'] is ff2.tree['my_array']
        assert_array_equal(ff.tree['my_array'], ff2.tree['my_array'])
        assert ff.blocks[my_array] != ff2.blocks[my_array]

        ff2.tree['my_array'] = None
        assert_array_equal(ff.tree['my_array'], my_array)


def test_update_exceptions(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path)

    with asdf.AsdfFile().read(path) as ff:
        with pytest.raises(IOError):
            ff.update()

    with asdf.AsdfFile(tree) as ff:
        buff = io.BytesIO()
        ff.write_to(buff)
        ff.update()

    with pytest.raises(ValueError):
        asdf.AsdfFile().update()


def test_get_data_from_closed_file(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    my_array = np.arange(0, 64).reshape((8, 8))

    tree = {'my_array': my_array}
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path)

    with asdf.AsdfFile().read(path) as ff:
        pass

    with pytest.raises(IOError):
        assert_array_equal(my_array, ff.tree['my_array'])


def test_seek_until_on_block_boundary():
    # Create content where the first block begins on a
    # file-reading-block boundary.

    content = b"""#ASDF 0.1.0
%YAML 1.2
%TAG ! tag:stsci.edu:asdf/0.1.0/
--- !core/asdf
foo : bar
...
"""
    content += (b'\0' * (io.DEFAULT_BUFFER_SIZE - 2) +
                constants.BLOCK_MAGIC + b'\0\x30' + b'\0' * 50)

    buff = io.BytesIO(content)
    ff = asdf.AsdfFile.read(buff)
    assert len(ff.blocks) == 1

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    ff = asdf.AsdfFile.read(fd)
    assert len(ff.blocks) == 1


def test_checksum(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    my_array = np.random.rand(8, 8)
    tree = {'my_array': my_array}
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path)

    with asdf.AsdfFile.read(path, validate_checksums=True) as ff:
        assert type(ff.blocks._blocks[0].checksum) == bytes
        assert ff.blocks._blocks[0].checksum == \
            b'\xcaM\\\xb8t_L|\x00\n+\x01\xf1\xcfP1'


def test_checksum_update(tmpdir):
    tmpdir = str(tmpdir)
    path = os.path.join(tmpdir, 'test.asdf')

    my_array = np.arange(0, 64).reshape((8, 8))

    tree = {'my_array': my_array}
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(path)
        my_array[7, 7] = 0.0
        # update() should update the checksum, even if the data itself
        # is memmapped and isn't expressly re-written.
        ff.update()

    with asdf.AsdfFile.read(path, validate_checksums=True) as ff:
        assert ff.blocks._blocks[0].checksum == \
            b'T\xaf~[\x90\x8a\x88^\xc2B\x96D,N\xadL'
