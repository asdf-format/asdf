# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import io
import os

from astropy.extern import six
from astropy.tests.helper import pytest

import numpy as np

from .. import finf
from .. import generic_io
from . import helpers


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
    content = b"""%FINF 0.1.0
%YAML 1.2
%TAG ! tag:stsci.edu,2014:finf/0.1.0/
--- !finf
foo: bar
    """
    path = os.path.join(str(tmpdir), 'test.finf')

    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        finf.FinfFile.read(buff)

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    with pytest.raises(ValueError):
        finf.FinfFile.read(fd)

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            finf.FinfFile.read(fd)


def test_no_finf_header(tmpdir):
    content = b"What? This ain't no FINF file"

    path = os.path.join(str(tmpdir), 'test.finf')

    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        finf.FinfFile.read(buff)

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            finf.FinfFile.read(fd)


def test_no_finf_blocks(tmpdir):
    content = b"""%FINF 0.1.0
%YAML 1.2
%TAG ! tag:stsci.edu,2014:finf/0.1.0/
--- !finf
foo: bar
...
XXXXXXXX
    """

    path = os.path.join(str(tmpdir), 'test.finf')

    buff = io.BytesIO(content)
    ff = finf.FinfFile.read(buff)
    assert len(ff.blocks) == 0

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    ff = finf.FinfFile.read(fd)
    assert len(ff.blocks) == 0

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        ff = finf.FinfFile.read(fd)
    assert len(ff.blocks) == 0


def test_invalid_source():
    buff = io.BytesIO()

    ff = finf.FinfFile(_get_small_tree())
    ff.write_to(buff)

    buff.seek(0)
    ff2 = finf.FinfFile.read(buff)

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
    buff = io.BytesIO(b"%FINF 0.1.0\n")
    buff.seek(0)

    ff = finf.FinfFile.read(buff)

    assert ff.tree == {}
    assert len(ff.blocks) == 0


def test_junk_file():
    buff = io.BytesIO(b"%FINF 0.1.0\nFOO")
    buff.seek(0)

    with pytest.raises(IOError):
        finf.FinfFile.read(buff)


def test_block_mismatch():
    # This is a file with a single small block, followed by something
    # that has an invalid block magic number.

    buff = io.BytesIO(
        b'%FINF 0.1.0\n\xd3BLK\x00\x28\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0FOO')

    buff.seek(0)
    with pytest.raises(ValueError):
        finf.FinfFile.read(buff)


def test_block_header_too_small():
    # The block header size must be at least 40

    buff = io.BytesIO(
        b'%FINF 0.1.0\n\xd3BLK\0\0')

    buff.seek(0)
    with pytest.raises(ValueError):
        finf.FinfFile.read(buff)


if six.PY2:
    def test_file_already_closed(tmpdir):
        # Test that referencing specific blocks in another finf file
        # works.
        tree = _get_small_tree()

        path = os.path.join(str(tmpdir), 'test.finf')
        ff = finf.FinfFile(tree)
        ff.write_to(path)

        with open(path, 'rb') as fd:
            ff2 = finf.FinfFile.read(fd)

        with pytest.raises(IOError):
            str(ff2.tree['science_data'][:])
