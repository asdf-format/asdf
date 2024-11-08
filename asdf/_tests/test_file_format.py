import io
import os

import pytest

import asdf
from asdf import generic_io


def test_no_yaml_end_marker(tmp_path):
    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo: bar...baz
baz: 42
    """
    path = os.path.join(str(tmp_path), "test.asdf")

    buff = io.BytesIO(content)
    with pytest.raises(ValueError, match=r"End of YAML marker not found"), asdf.open(buff):
        pass

    buff.seek(0)
    with pytest.raises(ValueError, match=r"End of YAML marker not found"), asdf.open(buff):
        pass

    with open(path, "wb") as fd:
        fd.write(content)

    with open(path, "rb") as fd, pytest.raises(ValueError, match=r"End of YAML marker not found"), asdf.open(fd):
        pass


def test_no_final_newline(tmp_path):
    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo: ...bar...
baz: 42
..."""
    path = os.path.join(str(tmp_path), "test.asdf")

    buff = io.BytesIO(content)
    with asdf.open(buff) as ff:
        assert len(ff.tree) == 2

    buff.seek(0)
    fd = generic_io.InputStream(buff, "r")
    with asdf.open(fd) as ff:
        assert len(ff.tree) == 2

    with open(path, "wb") as fd:
        fd.write(content)

    with open(path, "rb") as fd, asdf.open(fd) as ff:
        assert len(ff.tree) == 2


def test_no_asdf_header(tmp_path):
    content = b"What? This ain't no ASDF file"

    path = os.path.join(str(tmp_path), "test.asdf")

    buff = io.BytesIO(content)
    with pytest.raises(
        ValueError,
        match=r"Does not appear to be a ASDF file.",
    ):
        asdf.open(buff)

    with open(path, "wb") as fd:
        fd.write(content)

    with (
        open(path, "rb") as fd,
        pytest.raises(
            ValueError,
            match=r"Does not appear to be a ASDF file.",
        ),
    ):
        asdf.open(fd)


def test_empty_file():
    buff = io.BytesIO(b"#ASDF 1.0.0\n")
    buff.seek(0)

    with asdf.open(buff) as ff:
        assert ff.tree == {}
        assert len(ff._blocks.blocks) == 0

    buff = io.BytesIO(b"#ASDF 1.0.0\n#ASDF_STANDARD 1.0.0")
    buff.seek(0)

    with asdf.open(buff) as ff:
        assert ff.tree == {}
        assert len(ff._blocks.blocks) == 0


def test_not_asdf_file():
    buff = io.BytesIO(b"SIMPLE")
    buff.seek(0)

    with (
        pytest.raises(
            ValueError,
            match=r"Does not appear to be a ASDF file.",
        ),
        asdf.open(buff),
    ):
        pass

    buff = io.BytesIO(b"SIMPLE\n")
    buff.seek(0)

    with (
        pytest.raises(
            ValueError,
            match=r"Does not appear to be a ASDF file.",
        ),
        asdf.open(buff),
    ):
        pass


def test_junk_file():
    buff = io.BytesIO(b"#ASDF 1.0.0\nFOO")
    buff.seek(0)

    with pytest.raises(ValueError, match=r"Invalid content between header and tree"), asdf.open(buff):
        pass


def test_invalid_header_version():
    buff = io.BytesIO(b"#ASDF foo\n")
    buff.seek(0)

    with pytest.raises(ValueError, match=r"Unparsable version in ASDF file"), asdf.open(buff):
        pass


def test_block_mismatch():
    # This is a file with a single small block, followed by something
    # that has an invalid block magic number.

    buff = io.BytesIO(
        b"#ASDF 1.0.0\n\xd3BLK\x00\x28\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\x01"
        b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0FOOBAR",
    )

    buff.seek(0)
    with pytest.raises(ValueError, match=r"Header size must be >= 48"), asdf.open(buff):
        pass


def test_block_header_too_small():
    # The block header size must be at least 40

    buff = io.BytesIO(b"#ASDF 1.0.0\n\xd3BLK\0\0")

    buff.seek(0)
    with pytest.raises(ValueError, match=r"Header size must be >= 48"), asdf.open(buff):
        pass


def test_invalid_version(tmp_path):
    content = b"""#ASDF 0.1.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-0.1.0
foo : bar
..."""
    buff = io.BytesIO(content)
    with pytest.raises(ValueError, match=r"Unsupported ASDF file format version*"), asdf.open(buff):
        pass


def test_valid_version(tmp_path):
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
