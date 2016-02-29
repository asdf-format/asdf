# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os
import re
import sys

try:
    import psutil
except ImportError:
    HAS_PSUTIL = False
else:
    HAS_PSUTIL = True

import six
import pytest

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True

import numpy as np
from numpy import ma
from numpy.testing import assert_array_equal

import jsonschema

import yaml

from ....tests import helpers
from .... import asdf
from .... import util

from .. import ndarray


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


class CustomExtension:
    @property
    def types(self):
        return []

    @property
    def tag_mapping(self):
        return [('tag:nowhere.org:custom',
                 'http://nowhere.org/schemas/custom{tag_suffix}')]

    @property
    def url_mapping(self):
        return [(
            'http://nowhere.org/schemas/custom/',
            util.filepath_to_url(TEST_DATA_PATH) + '/{url_suffix}.yaml')]


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
    with asdf.AsdfFile.open(buff) as ff:
        ff.run_hook('reserve_blocks')

        # repr and str shouldn't load data
        str(ff.tree['science_data'])
        repr(ff.tree)

        for block in ff.blocks.internal_blocks:
            assert block._data is None


def test_table_inline(tmpdir):
    table = np.array(
        [(0, 1, (2, 3)), (4, 5, (6, 7))],
        dtype=[(str('MINE'), np.int8),
               (str(''), np.float64),
               (str('arr'), '>i4', (2,))])

    tree = {'table_data': table}

    def check_raw_yaml(content):
        tree = yaml.load(
            re.sub(br'!core/\S+', b'', content))

        assert tree['table_data'] == {
            'datatype': [
                {'datatype': 'int8', 'name': 'MINE'},
                {'datatype': 'float64', 'name': 'f1'},
                {'datatype': 'int32', 'name': 'arr', 'shape': [2]}
                ],
            'data': [[0, 1.0, [2, 3]], [4, 5.0, [6, 7]]],
            'shape': [2]
            }

    helpers.assert_roundtrip_tree(
        tree, tmpdir, None, check_raw_yaml, {'auto_inline': 64})


@pytest.mark.skipif('not HAS_ASTROPY')
def test_auto_inline_recursive(tmpdir):
    from astropy.modeling import models
    aff = models.AffineTransformation2D(matrix=[[1, 2], [3, 4]])
    tree = {'test': aff}

    def check_asdf(asdf):
        assert len(list(asdf.blocks.internal_blocks)) == 0

    helpers.assert_roundtrip_tree(
        tree, tmpdir, check_asdf, None, {'auto_inline': 64})


def test_table(tmpdir):
    table = np.array(
        [(0, 1, (2, 3)), (4, 5, (6, 7))],
        dtype=[(str('MINE'), np.int8),
               (str(''), np.float64),
               (str('arr'), '>i4', (2,))])

    tree = {'table_data': table}

    def check_raw_yaml(content):
        tree = yaml.load(
            re.sub(br'!core/\S+', b'', content))

        assert tree['table_data'] == {
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
        dtype=[(str('A'), np.int64),
               (str('B'), [(str('C'), np.int64), (str('D'), np.int64)])])

    tree = {'table_data': table}

    def check_raw_yaml(content):
        tree = yaml.load(
            re.sub(br'!core/\S+', b'', content))

        assert tree['table_data'] == {
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

    ff = asdf.AsdfFile(tree)
    ff.blocks.set_array_storage(ff.blocks[tree['science_data']], 'inline')
    ff.write_to(buff)

    buff.seek(0)
    with asdf.AsdfFile.open(buff, mode='rw') as ff:
        helpers.assert_tree_match(tree, ff.tree)
        assert len(list(ff.blocks.internal_blocks)) == 0
        buff = io.BytesIO()
        ff.write_to(buff)

    assert b'[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]' in buff.getvalue()


def test_inline_bare():
    content = "arr: !core/ndarray-1.0.0 [[1, 2, 3, 4], [5, 6, 7, 8]]"
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff) as ff:
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


def test_mask_arbitrary():
    content = """
    arr: !core/ndarray-1.0.0
      data: [[1, 2, 3, 1234], [5, 6, 7, 8]]
      mask: 1234
    """

    buff = helpers.yaml_to_asdf(content)
    with asdf.AsdfFile.open(buff) as ff:
        assert_array_equal(
            ff.tree['arr'].mask,
            [[False, False, False, True], [False, False, False, False]])


def test_mask_nan():
    content = """
    arr: !core/ndarray-1.0.0
      data: [[1, 2, 3, .NaN], [5, 6, 7, 8]]
      mask: .NaN
    """

    buff = helpers.yaml_to_asdf(content)
    with asdf.AsdfFile.open(buff) as ff:
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
    content = "arr: !core/ndarray-1.0.0 ['a', 'b', 'c']"
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff) as ff:
        assert_array_equal(ff.tree['arr']._make_array(), ['a', 'b', 'c'])


def test_inline_structured():
    content = """
    arr: !core/ndarray-1.0.0
        datatype: [['ascii', 4], uint16, uint16, ['ascii', 4]]
        data: [[M110, 110, 205, And],
               [ M31,  31, 224, And],
               [ M32,  32, 221, And],
               [M103, 103, 581, Cas]]"""

    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff) as ff:
        assert ff.tree['arr']['f1'].dtype.char == 'H'


def test_simple_table():
    table = np.array(
        [(10.683262825012207, 41.2674560546875, 0.13, 0.12, 213.916),
         (10.682777404785156, 41.270111083984375, 0.1, 0.09, 306.825),
         (10.684737205505371, 41.26903533935547, 0.08, 0.07, 96.656),
         (10.682382583618164, 41.26792526245117, 0.1, 0.09, 237.145),
         (10.686025619506836, 41.26922607421875, 0.13, 0.12, 79.581),
         (10.685656547546387, 41.26955032348633, 0.13, 0.12, 55.219),
         (10.684028625488281, 41.27090072631836, 0.13, 0.12, 345.269),
         (10.687610626220703, 41.270301818847656, 0.18, 0.14, 60.192)],
        dtype=[
            (str('ra'), str('<f4')),
            (str('dec'), str('<f4')),
            (str('err_maj'), str('<f8')),
            (str('err_min'), str('<f8')),
            (str('angle'), str('<f8'))])

    tree = {'table': table}
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(table, 'inline')
    ff.write_to(io.BytesIO())


def test_unicode_to_list(tmpdir):
    arr = np.array(['', '𐀠'], dtype='<U')
    tree = {
        'unicode': arr
    }

    fd = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(arr, 'inline')
    ff.write_to(fd)
    fd.seek(0)

    with asdf.AsdfFile.open(fd) as ff:
        ff.resolve_and_inline()
        ff.write_to(io.BytesIO())


def test_inline_masked_array(tmpdir):
    tree = {'test': ma.array([1, 2, 3], mask=[0, 1, 0])}

    f = asdf.AsdfFile(tree)
    f.set_array_storage(tree['test'], 'inline')
    f.write_to('masked.asdf')

    with asdf.AsdfFile.open('masked.asdf') as f2:
        assert len(list(f2.blocks.internal_blocks)) == 0
        assert_array_equal(f.tree['test'], f2.tree['test'])

    with open('masked.asdf', 'rb') as fd:
        assert b'null' in fd.read()


@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
def test_masked_array_stay_open_bug(tmpdir):
    tmppath = os.path.join(str(tmpdir), 'masked.asdf')

    tree = {
        'test': np.ma.array([1, 2, 3], mask=[False, True, False])
    }

    f = asdf.AsdfFile(tree)
    f.write_to(tmppath)

    p = psutil.Process()
    orig_open = p.open_files()

    for i in range(3):
        with asdf.AsdfFile.open(tmppath) as f2:
            np.sum(f2.tree['test'])

    assert len(p.open_files()) == len(orig_open)


def test_masked_array_repr(tmpdir):
    tmppath = os.path.join(str(tmpdir), 'masked.asdf')

    tree = {
        'array': np.arange(10),
        'masked': np.ma.array([1, 2, 3], mask=[False, True, False])
    }

    asdf.AsdfFile(tree).write_to(tmppath)

    with asdf.AsdfFile.open(tmppath) as ff:
        assert 'masked array' in repr(ff.tree['masked'])


def test_operations_on_ndarray_proxies(tmpdir):
    tmppath = os.path.join(str(tmpdir), 'test.asdf')

    tree = {
        'array': np.arange(10)
    }

    asdf.AsdfFile(tree).write_to(tmppath)

    with asdf.AsdfFile.open(tmppath) as ff:
        x = ff.tree['array'] * 2
        assert_array_equal(x, np.arange(10) * 2)

    with asdf.AsdfFile.open(tmppath) as ff:
        x = -ff.tree['array']
        assert_array_equal(x, -np.arange(10))

    with asdf.AsdfFile.open(tmppath, mode='rw') as ff:
        ff.tree['array'][2] = 4
        x = np.arange(10)
        x[2] = 4
        assert_array_equal(ff.tree['array'], x)


def test_mask_datatype(tmpdir):
    content = """
        arr: !core/ndarray-1.0.0
            data: [1, 2, 3]
            dtype: int32
            mask: !core/ndarray-1.0.0
                data: [true, true, false]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff) as ff:
        pass


def test_invalid_mask_datatype(tmpdir):
    content = """
        arr: !core/ndarray-1.0.0
            data: [1, 2, 3]
            dtype: int32
            mask: !core/ndarray-1.0.0
                data: ['a', 'b', 'c']
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff) as ff:
            pass


def test_ndim_validation(tmpdir):
    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        a: !core/ndarray-1.0.0
           data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        a: !core/ndarray-1.0.0
           shape: [1, 3]
           data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        b: !core/ndarray-1.0.0
           data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        b: !core/ndarray-1.0.0
           data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        b: !core/ndarray-1.0.0
           data: [[[1, 2, 3]]]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass


def test_datatype_validation(tmpdir):
    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: float32
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: float64
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: int16
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        b: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: int16
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass


def test_structured_datatype_validation(tmpdir):
    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int64
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [[1, 'a', 0], [2, 'b', 1], [3, 'c', 2]]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
             - name: c
               datatype: float64
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        d: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        d: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int16
             - name: b
               datatype: ['ascii', 16]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.AsdfFile.open(buff, extensions=CustomExtension()) as ff:
        pass


def test_string_inline():
    x = np.array([b'a', b'b', b'c'])
    l = ndarray.numpy_array_to_list(x)

    for entry in l:
        assert isinstance(entry, six.text_type)


def test_inline_shape_mismatch():
    content = """
    arr: !core/ndarray-1.0.0
      data: [1, 2, 3]
      shape: [2]
    """

    buff = helpers.yaml_to_asdf(content)
    with pytest.raises(ValueError):
        with asdf.AsdfFile.open(buff) as ff:
            pass
