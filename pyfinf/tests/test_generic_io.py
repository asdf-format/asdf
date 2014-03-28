# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

from astropy.tests.helper import pytest

import numpy as np

from .. import finf
from .. import generic_io

from . import helpers


def _roundtrip(get_write_fd, get_read_fd):
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2]
        }

    with get_write_fd() as fd:
        finf.FinfFile(tree).write_to(fd)

    with get_read_fd() as fd:
        ff = finf.FinfFile.read(fd)

        assert len(ff._blocks) == 1

        helpers.assert_tree_match(tree, ff.tree)

    return ff


def test_path(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        f = generic_io.get_file(path, mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    def get_read_fd():
        f = generic_io.get_file(path, mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    ff = _roundtrip(get_write_fd, get_read_fd)

    ff._blocks[0].data
    assert isinstance(ff._blocks[0]._data, np.core.memmap)


def test_open(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        f = generic_io.get_file(open(path, 'wb'), mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    def get_read_fd():
        f = generic_io.get_file(open(path, 'rb'), mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    ff = _roundtrip(get_write_fd, get_read_fd)

    assert isinstance(ff._blocks[0]._data, np.core.memmap)


def test_open_fail(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    with open(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='w')


def test_open_fail2(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    with io.open(path, 'w') as fd:
        with pytest.raises(ValueError):
            generic_io.get_file(fd, mode='w')


def test_io_open(tmpdir):
    path = os.path.join(str(tmpdir), 'test.finf')

    def get_write_fd():
        f = generic_io.get_file(io.open(path, 'wb'), mode='w')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    def get_read_fd():
        f = generic_io.get_file(io.open(path, 'rb'), mode='r')
        assert isinstance(f, generic_io.RealFile)
        assert f._uri == path
        return f

    ff = _roundtrip(get_write_fd, get_read_fd)

    assert isinstance(ff._blocks[0]._data, np.core.memmap)


def test_bytes_io():
    buff = io.BytesIO()

    def get_write_fd():
        f = generic_io.get_file(buff, mode='w')
        assert isinstance(f, generic_io.MemoryIO)
        return f

    def get_read_fd():
        buff.seek(0)
        f = generic_io.get_file(buff, mode='r')
        assert isinstance(f, generic_io.MemoryIO)
        return f

    ff = _roundtrip(get_write_fd, get_read_fd)

    assert not isinstance(ff._blocks[0]._data, np.core.memmap)
    assert isinstance(ff._blocks[0]._data, np.ndarray)


def test_streams():
    buff = io.BytesIO()

    def get_write_fd():
        return generic_io.OutputStream(buff)

    def get_read_fd():
        print(repr(buff.getvalue()))
        buff.seek(0)
        return generic_io.InputStream(buff)

    ff = _roundtrip(get_write_fd, get_read_fd)

    assert not isinstance(ff._blocks[0]._data, np.core.memmap)
    assert isinstance(ff._blocks[0]._data, np.ndarray)
