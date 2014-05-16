# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

from astropy.tests.helper import pytest

import numpy as np
from numpy.testing import assert_array_equal

from .. import finf
from .. import generic_io
from .. import stream


def test_stream():
    buff = io.BytesIO()

    tree = {
        'stream': stream.Stream([6, 2], np.float64)
    }

    with finf.FinfFile(tree).write_to(buff) as ff:
        for i in range(100):
            ff.write_to_stream(np.array([i] * 12, np.float64).tostring())

    buff.seek(0)

    with finf.FinfFile().read(buff) as ff:
        assert len(ff.blocks) == 1
        assert ff.tree['stream'].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_stream_write_nothing():
    # Test that if you write nothing, you get a zero-length array

    buff = io.BytesIO()

    tree = {
        'stream': stream.Stream([6, 2], np.float64)
    }

    with finf.FinfFile(tree).write_to(buff) as ff:
        pass

    buff.seek(0)

    with finf.FinfFile().read(buff) as ff:
        assert len(ff.blocks) == 1
        assert ff.tree['stream'].shape == (0, 6, 2)


def test_stream_twice():
    # Test that if you write nothing, you get a zero-length array

    buff = io.BytesIO()

    tree = {
        'stream': stream.Stream([6, 2], np.uint8),
        'stream2': stream.Stream([12, 2], np.uint8)
    }

    with finf.FinfFile(tree).write_to(buff) as ff:
        for i in range(100):
            ff.write_to_stream(np.array([i] * 12, np.uint8).tostring())

    buff.seek(0)

    with finf.FinfFile().read(buff) as ff:
        assert len(ff.blocks) == 1
        assert ff.tree['stream'].shape == (100, 6, 2)
        assert ff.tree['stream2'].shape == (50, 12, 2)


def test_stream_with_nonstream():
    buff = io.BytesIO()

    tree = {
        'nonstream': np.array([1, 2, 3, 4], np.int64),
        'stream': stream.Stream([6, 2], np.float64)
    }

    with finf.FinfFile(tree).write_to(buff) as ff:
        for i in range(100):
            ff.write_to_stream(np.array([i] * 12, np.float64).tostring())

    buff.seek(0)

    with finf.FinfFile().read(buff) as ff:
        assert len(ff.blocks) == 2
        assert_array_equal(ff.tree['nonstream'], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree['stream'].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_stream_real_file(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    tree = {
        'nonstream': np.array([1, 2, 3, 4], np.int64),
        'stream': stream.Stream([6, 2], np.float64)
    }

    with finf.FinfFile(tree).write_to(path) as ff:
        for i in range(100):
            ff.write_to_stream(np.array([i] * 12, np.float64).tostring())

    with finf.FinfFile().read(path) as ff:
        assert len(ff.blocks) == 2
        assert_array_equal(ff.tree['nonstream'], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree['stream'].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_stream_to_stream():
    tree = {
        'nonstream': np.array([1, 2, 3, 4], np.int64),
        'stream': stream.Stream([6, 2], np.float64)
    }

    buff = io.BytesIO()

    with finf.FinfFile(tree).write_to(generic_io.OutputStream(buff)) as ff:
        for i in range(100):
            ff.write_to_stream(np.array([i] * 12, np.float64).tostring())

    buff.seek(0)

    with finf.FinfFile().read(generic_io.InputStream(buff, 'r')) as ff:
        assert len(ff.blocks) == 2
        assert_array_equal(ff.tree['nonstream'], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree['stream'].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_array_to_stream():
    tree = {
        'stream': np.array([1, 2, 3, 4], np.int64),
    }

    buff = io.BytesIO()

    with finf.FinfFile(tree) as ff:
        ff.blocks[tree['stream']].block_type = 'streamed'
        ff.write_to(buff)
        ff.write_to_stream(np.array([5, 6, 7, 8], np.int64).tostring())

    buff.seek(0)

    with finf.FinfFile().read(buff) as ff:
        assert_array_equal(ff.tree['stream'], [1, 2, 3, 4, 5, 6, 7, 8])
        buff.seek(0)
        ff.write_to(buff)
        assert b"shape: ['*']" in buff.getvalue()


def test_too_many_streams():
    tree = {
        'stream1': np.array([1, 2, 3, 4], np.int64),
        'stream2': np.array([1, 2, 3, 4], np.int64)
    }

    buff = io.BytesIO()

    with finf.FinfFile(tree) as ff:
        ff.blocks[tree['stream1']].block_type = 'streamed'
        ff.blocks[tree['stream2']].block_type = 'streamed'
        with pytest.raises(ValueError):
            ff.write_to(buff)
