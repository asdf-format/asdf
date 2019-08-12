# -*- coding: utf-8 -*-

import os
import io

import pytest

import asdf
from asdf import generic_io


def test_no_yaml_end_marker(tmpdir):
    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo: bar...baz
baz: 42
    """
    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    with pytest.raises(ValueError):
        with asdf.open(fd):
            pass

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            with asdf.open(fd):
                pass


def test_no_final_newline(tmpdir):
    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo: ...bar...
baz: 42
..."""
    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with asdf.open(buff) as ff:
        assert len(ff.tree) == 2

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    with asdf.open(fd) as ff:
        assert len(ff.tree) == 2

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with asdf.open(fd) as ff:
            assert len(ff.tree) == 2


def test_no_asdf_header(tmpdir):
    content = b"What? This ain't no ASDF file"

    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        asdf.open(buff)

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with pytest.raises(ValueError):
            asdf.open(fd)


def test_no_asdf_blocks(tmpdir):
    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo: bar
...
XXXXXXXX
    """

    path = os.path.join(str(tmpdir), 'test.asdf')

    buff = io.BytesIO(content)
    with asdf.open(buff) as ff:
        assert len(ff.blocks) == 0

    buff.seek(0)
    fd = generic_io.InputStream(buff, 'r')
    with asdf.open(fd) as ff:
        assert len(ff.blocks) == 0

    with open(path, 'wb') as fd:
        fd.write(content)

    with open(path, 'rb') as fd:
        with asdf.open(fd) as ff:
            assert len(ff.blocks) == 0


def test_invalid_source(small_tree):
    buff = io.BytesIO()

    ff = asdf.AsdfFile(small_tree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ff.write_to(buff, all_array_storage='internal')

    buff.seek(0)
    with asdf.open(buff) as ff2:
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
    buff = io.BytesIO(b"#ASDF 1.0.0\n")
    buff.seek(0)

    with asdf.open(buff) as ff:
        assert ff.tree == {}
        assert len(ff.blocks) == 0

    buff = io.BytesIO(b"#ASDF 1.0.0\n#ASDF_STANDARD 1.0.0")
    buff.seek(0)

    with asdf.open(buff) as ff:
        assert ff.tree == {}
        assert len(ff.blocks) == 0


def test_not_asdf_file():
    buff = io.BytesIO(b"SIMPLE")
    buff.seek(0)

    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass

    buff = io.BytesIO(b"SIMPLE\n")
    buff.seek(0)

    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass


def test_junk_file():
    buff = io.BytesIO(b"#ASDF 1.0.0\nFOO")
    buff.seek(0)

    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass


def test_block_mismatch():
    # This is a file with a single small block, followed by something
    # that has an invalid block magic number.

    buff = io.BytesIO(
        b'#ASDF 1.0.0\n\xd3BLK\x00\x28\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0FOOBAR')

    buff.seek(0)
    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass


def test_block_header_too_small():
    # The block header size must be at least 40

    buff = io.BytesIO(
        b'#ASDF 1.0.0\n\xd3BLK\0\0')

    buff.seek(0)
    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass


def test_invalid_version(tmpdir):
    content = b"""#ASDF 0.1.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-0.1.0
foo : bar
..."""
    buff = io.BytesIO(content)
    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass


def test_valid_version(tmpdir):
    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo : bar
..."""
    buff = io.BytesIO(content)
    with asdf.open(buff) as ff:
        version = ff.file_format_version

    assert version.major == 1
    assert version.minor == 0
    assert version.patch == 0
