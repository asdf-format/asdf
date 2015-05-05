# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

from astropy.tests.helper import pytest
from astropy import table

from .... import asdf
from ....tests import helpers


def test_table(tmpdir):
    data_rows = [(1, 2.0, 'x'),
                 (4, 5.0, 'y'),
                 (5, 8.2, 'z')]
    t = table.Table(rows=data_rows, names=('a', 'b', 'c'),
                    dtype=('i4', 'f8', 'S1'))
    t.columns['a'].description = 'RA'
    t.columns['a'].unit = 'degree'
    t.columns['a'].meta = {'foo': 'bar'}
    t.columns['c'].description = 'Some description of some sort'

    def asdf_check(ff):
        assert len(ff.blocks) == 3

    helpers.assert_roundtrip_tree({'table': t}, tmpdir, asdf_check)


def test_table_row_order(tmpdir):
    a = np.array([(1, 2.0, 'x'),
                  (4, 5.0, 'y'),
                  (5, 8.2, 'z')],
                 dtype=[(str('a'), str('<i4')),
                        (str('b'), str('<f8')),
                        (str('c'), str('|S1'))])

    t = table.Table(a, copy=False)
    t.columns['a'].description = 'RA'
    t.columns['a'].unit = 'degree'
    t.columns['a'].meta = {'foo': 'bar'}
    t.columns['c'].description = 'Some description of some sort'

    def asdf_check(ff):
        assert len(ff.blocks) == 1

    helpers.assert_roundtrip_tree({'table': t}, tmpdir, asdf_check)


def test_table_inline(tmpdir):
    data_rows = [(1, 2.0, 'x'),
                 (4, 5.0, 'y'),
                 (5, 8.2, 'z')]
    t = table.Table(rows=data_rows, names=('a', 'b', 'c'),
                    dtype=('i4', 'f8', 'S1'))
    t.columns['a'].description = 'RA'
    t.columns['a'].unit = 'degree'
    t.columns['a'].meta = {'foo': 'bar'}
    t.columns['c'].description = 'Some description of some sort'

    def asdf_check(ff):
        assert len(list(ff.blocks.internal_blocks)) == 0

    helpers.assert_roundtrip_tree({'table': t}, tmpdir, asdf_check,
                                  write_options={'auto_inline': 64})


def test_mismatched_columns():
    yaml = """
table: !core/table
  columns:
  - !core/column
    data: !core/ndarray
      data: [0, 1, 2]
    name: a
  - !core/column
    data: !core/ndarray
      data: [0, 1, 2, 3]
    name: b
    """

    buff = helpers.yaml_to_asdf(yaml)

    with pytest.raises(ValueError):
        with asdf.AsdfFile.open(buff) as ff:
            pass


def test_masked_table(tmpdir):
    data_rows = [(1, 2.0, 'x'),
                 (4, 5.0, 'y'),
                 (5, 8.2, 'z')]
    t = table.Table(rows=data_rows, names=('a', 'b', 'c'),
                    dtype=('i4', 'f8', 'S1'), masked=True)
    t.columns['a'].description = 'RA'
    t.columns['a'].unit = 'degree'
    t.columns['a'].meta = {'foo': 'bar'}
    t.columns['a'].mask = [True, False, True]
    t.columns['c'].description = 'Some description of some sort'

    def asdf_check(ff):
        assert len(ff.blocks) == 4

    helpers.assert_roundtrip_tree({'table': t}, tmpdir, asdf_check)
