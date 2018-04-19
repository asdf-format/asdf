# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io
import os

import numpy as np
from numpy.testing import assert_array_equal

import pytest

import asdf
from asdf import generic_io
from asdf import stream


def test_stream():
    buff = io.BytesIO()

    tree = {
        'stream': stream.Stream([6, 2], np.float64)
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    for i in range(100):
        buff.write(np.array([i] * 12, np.float64).tostring())

    buff.seek(0)

    with asdf.AsdfFile.open(buff) as ff:
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

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    buff.seek(0)

    with asdf.AsdfFile().open(buff) as ff:
        assert len(ff.blocks) == 1
        assert ff.tree['stream'].shape == (0, 6, 2)


def test_stream_twice():
    # Test that if you write nothing, you get a zero-length array

    buff = io.BytesIO()

    tree = {
        'stream': stream.Stream([6, 2], np.uint8),
        'stream2': stream.Stream([12, 2], np.uint8)
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    for i in range(100):
        buff.write(np.array([i] * 12, np.uint8).tostring())

    buff.seek(0)

    ff = asdf.AsdfFile().open(buff)
    assert len(ff.blocks) == 1
    assert ff.tree['stream'].shape == (100, 6, 2)
    assert ff.tree['stream2'].shape == (50, 12, 2)


def test_stream_with_nonstream():
    buff = io.BytesIO()

    tree = {
        'nonstream': np.array([1, 2, 3, 4], np.int64),
        'stream': stream.Stream([6, 2], np.float64)
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    for i in range(100):
        buff.write(np.array([i] * 12, np.float64).tostring())

    buff.seek(0)

    with asdf.AsdfFile().open(buff) as ff:
        assert len(ff.blocks) == 1
        assert_array_equal(ff.tree['nonstream'], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree['stream'].shape == (100, 6, 2)
        assert len(ff.blocks) == 2
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_stream_real_file(tmpdir):
    path = os.path.join(str(tmpdir), 'test.asdf')

    tree = {
        'nonstream': np.array([1, 2, 3, 4], np.int64),
        'stream': stream.Stream([6, 2], np.float64)
    }

    with open(path, 'wb') as fd:
        ff = asdf.AsdfFile(tree)
        ff.write_to(fd)
        for i in range(100):
            fd.write(np.array([i] * 12, np.float64).tostring())

    with asdf.AsdfFile().open(path) as ff:
        assert len(ff.blocks) == 1
        assert_array_equal(ff.tree['nonstream'], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree['stream'].shape == (100, 6, 2)
        assert len(ff.blocks) == 2
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_stream_to_stream():
    tree = {
        'nonstream': np.array([1, 2, 3, 4], np.int64),
        'stream': stream.Stream([6, 2], np.float64)
    }

    buff = io.BytesIO()
    fd = generic_io.OutputStream(buff)

    ff = asdf.AsdfFile(tree)
    ff.write_to(fd)
    for i in range(100):
        fd.write(np.array([i] * 12, np.float64).tostring())

    buff.seek(0)

    with asdf.AsdfFile().open(generic_io.InputStream(buff, 'r')) as ff:
        assert len(ff.blocks) == 2
        assert_array_equal(ff.tree['nonstream'], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree['stream'].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree['stream']):
            assert np.all(row == i)


def test_array_to_stream(tmpdir):
    tree = {
        'stream': np.array([1, 2, 3, 4], np.int64),
    }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree['stream'], 'streamed')
    ff.write_to(buff)
    buff.write(np.array([5, 6, 7, 8], np.int64).tostring())

    buff.seek(0)
    ff = asdf.AsdfFile().open(generic_io.InputStream(buff))
    assert_array_equal(ff.tree['stream'], [1, 2, 3, 4, 5, 6, 7, 8])
    buff.seek(0)
    ff2 = asdf.AsdfFile(ff)
    ff2.write_to(buff)
    assert b"shape: ['*']" in buff.getvalue()

    with open(os.path.join(str(tmpdir), 'test.asdf'), 'wb') as fd:
        ff = asdf.AsdfFile(tree)
        ff.set_array_storage(tree['stream'], 'streamed')
        ff.write_to(fd)
        fd.write(np.array([5, 6, 7, 8], np.int64).tostring())

    with asdf.AsdfFile().open(os.path.join(str(tmpdir), 'test.asdf')) as ff:
        assert_array_equal(ff.tree['stream'], [1, 2, 3, 4, 5, 6, 7, 8])
        ff2 = asdf.AsdfFile(ff)
        ff2.write_to(buff)
        assert b"shape: ['*']" in buff.getvalue()


def test_too_many_streams():
    tree = {
        'stream1': np.array([1, 2, 3, 4], np.int64),
        'stream2': np.array([1, 2, 3, 4], np.int64)
    }

    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree['stream1'], 'streamed')
    with pytest.raises(ValueError):
        ff.set_array_storage(tree['stream2'], 'streamed')

def test_stream_repr_and_str():
    tree = {
        'stream': stream.Stream([16], np.int64)
    }

    ff = asdf.AsdfFile(tree)
    repr(ff.tree['stream'])
    str(ff.tree['stream'])
