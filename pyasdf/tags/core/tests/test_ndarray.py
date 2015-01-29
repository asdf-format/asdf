# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import sys

from astropy.extern import six

import numpy as np
from numpy import ma
from numpy.testing import assert_array_equal

import yaml

from ....tests import helpers
from .... import asdf

from .. import ndarray


def test_sharing(tmpdir):
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }

    def check_asdf(asdf):
        tree = asdf.tree

        assert_array_equal(tree['science_data'], x)
        assert_array_equal(tree['subset'], x[3:-3])
        assert_array_equal(tree['skipping'], x[::2])

        assert tree['science_data'].ctypes.data == tree['skipping'].ctypes.data

        assert len(list(asdf.blocks.internal_blocks)) == 1
        assert next(asdf.blocks.internal_blocks)._size == 80

        tree['science_data'][0] = 42
        assert tree['skipping'][0] == 42

    def check_raw_yaml(content):
        assert b'!core/ndarray' in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf, check_raw_yaml)


def test_byteorder(tmpdir):
    tree = {
        'bigendian': np.arange(0, 10, dtype=str('>f8')),
        'little': np.arange(0, 10, dtype=str('<f8')),
        }

    def check_asdf(asdf):
        tree = asdf.tree

        if sys.byteorder == 'little':
            assert tree['bigendian'].dtype.byteorder == '>'
            assert tree['little'].dtype.byteorder == '='
        else:
            assert tree['bigendian'].dtype.byteorder == '='
            assert tree['little'].dtype.byteorder == '<'

    def check_raw_yaml(content):
        assert b'byteorder: little' in content
        assert b'byteorder: big' in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf, check_raw_yaml)


def test_all_dtypes(tmpdir):
    tree = {}
    for byteorder in ('>', '<'):
        for dtype in ndarray._datatype_names.values():
            # Python 3 can't expose these dtypes in non-native byte
            # order, because it's using the new Python buffer
            # interface.
            if six.PY3 and dtype in ('c32', 'f16'):
                continue

            if dtype == 'b1':
                arr = np.array([True, False])
            else:
                arr = np.arange(0, 10, dtype=str(byteorder + dtype))

            tree[byteorder + dtype] = arr

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_dont_load_data():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }
    ff = asdf.AsdfFile(tree)

    buff = io.BytesIO()
    ff.write_to(buff)

    buff.seek(0)
    ff = asdf.AsdfFile.read(buff)

    ff.run_hook('pre_write')

    # repr and str shouldn't load data
    str(ff.tree['science_data'])
    repr(ff.tree)

    for block in ff.blocks.internal_blocks:
        assert block._data is None


def test_table(tmpdir):
    table = np.array(
        [(0, 1, (2, 3)), (4, 5, (6, 7))],
        dtype=[(str('MINE'), np.int8),
               (str(''), np.float64),
               (str('arr'), '>i4', (2,))])

    tree = {'table_data': table}

    def check_raw_yaml(content):
        content = b'\n'.join(content.splitlines()[4:-1])
        tree = yaml.load(content)

        assert tree == {
            'datatype': [
                {'byteorder': 'big', 'datatype': 'int8', 'name': 'MINE'},
                {'byteorder': 'little', 'datatype': 'float64', 'name': 'f1'},
                {'byteorder': 'big', 'datatype': 'int32', 'name': 'arr', 'shape': [2]}
                ],
            'shape': [2],
            'source': 0,
            'byteorder': 'big'
            }

    helpers.assert_roundtrip_tree(tree, tmpdir, None, check_raw_yaml)


def test_table_nested_fields(tmpdir):
    table = np.array(
        [(0, (1, 2)), (4, (5, 6)), (7, (8, 9))],
        dtype=[(str('A'), np.int),
               (str('B'), [(str('C'), np.int), (str('D'), np.int)])])

    tree = {'table_data': table}

    def check_raw_yaml(content):
        content = b'\n'.join(content.splitlines()[4:-1])
        tree = yaml.load(content)

        assert tree == {
            'datatype': [
                {'datatype': 'int64', 'name': 'A', 'byteorder': 'little'},
                {'datatype': [
                    {'datatype': 'int64', 'name': 'C', 'byteorder': 'little'},
                    {'datatype': 'int64', 'name': 'D', 'byteorder': 'little'}
                ], 'name': 'B', 'byteorder': 'big'}],
            'shape': [3],
            'source': 0,
            'byteorder': 'big'
        }

    helpers.assert_roundtrip_tree(tree, tmpdir, None, check_raw_yaml)


def test_inline():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }

    buff = io.BytesIO()

    with asdf.AsdfFile(tree) as ff:
        ff.blocks[tree['science_data']].array_storage = 'inline'
        ff.write_to(buff)

    buff.seek(0)
    with asdf.AsdfFile.read(buff, mode='rw') as ff:
        helpers.assert_tree_match(tree, ff.tree)
        assert len(list(ff.blocks.internal_blocks)) == 0
        buff = io.BytesIO()
        with asdf.AsdfFile(ff).write_to(buff):
            pass

    assert b'[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]' in buff.getvalue()


def test_inline_bare():
    content = "arr: !core/ndarray [[1, 2, 3, 4], [5, 6, 7, 8]]"
    buff = helpers.yaml_to_asdf(content)

    ff = asdf.AsdfFile.read(buff)

    assert_array_equal(ff.tree['arr'], [[1, 2, 3, 4], [5, 6, 7, 8]])


def test_mask_roundtrip(tmpdir):
    x = np.arange(0, 10, dtype=np.float)
    m = ma.array(x, mask=x > 5)
    tree = {
        'masked_array': m,
        'unmasked_array': x
        }

    def check_asdf(asdf):
        tree = asdf.tree

        m = tree['masked_array']
        x = tree['unmasked_array']

        print(m)
        print(m.mask)
        assert np.all(m.mask[6:])
        assert len(asdf.blocks) == 2

    helpers.assert_roundtrip_tree(tree, tmpdir, check_asdf)


def test_mask_nan():
    content = """
    arr: !core/ndarray
      data: [[1, 2, 3, .NaN], [5, 6, 7, 8]]
      mask: .NaN
    """

    buff = helpers.yaml_to_asdf(content)
    ff = asdf.AsdfFile.read(buff)

    assert_array_equal(
        ff.tree['arr'].mask,
        [[False, False, False, True], [False, False, False, False]])


def test_string(tmpdir):
    tree = {
        'ascii': np.array([b'foo', b'bar', b'baz']),
        'unicode': np.array(['სამეცნიერო', 'данные', 'வடிவம்'])
        }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_string_table(tmpdir):
    tree = {
        'table': np.array([(b'foo', 'სამეცნიერო', 42, 53.0)])
        }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_inline_string():
    content = "arr: !core/ndarray ['a', 'b', 'c']"
    buff = helpers.yaml_to_asdf(content)

    ff = asdf.AsdfFile.read(buff)

    assert_array_equal(ff.tree['arr']._make_array(), ['a', 'b', 'c'])


def test_inline_structured():
    content = """
    arr: !core/ndarray
        datatype: [['ascii', 4], uint16, uint16, ['ascii', 4]]
        data: [[M110, 110, 205, And],
               [ M31,  31, 224, And],
               [ M32,  32, 221, And],
               [M103, 103, 581, Cas]]"""

    buff = helpers.yaml_to_asdf(content)

    ff = asdf.AsdfFile.read(buff)

    assert ff.tree['arr']['f1'].dtype.char == 'H'
