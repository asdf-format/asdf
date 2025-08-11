import numpy as np
import pytest

import asdf
from asdf._commands import main


@pytest.fixture()
def valid_file_path(tmp_path):
    path = tmp_path / "valid_file.asdf"
    asdf.dump({"foo": 42, "arr": np.arange(42)}, path)
    return path


@pytest.fixture()
def invalid_file_path(tmp_path):
    # don't use asdf as we're intentionally making an invalid file
    contents = b"""#ASDF 1.0.0
#ASDF_STANDARD 1.6.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.1.0
arr: !core/ndarray-1.1.0
  data:
    nested: error
..."""
    path = tmp_path / "invalid_file.asdf"
    with path.open("wb") as f:
        f.write(contents)
    return path


@pytest.fixture()
def custom_schema_path(tmp_path):
    contents = """%YAML 1.1
---
id: "http://example.com/schemas/your-custom-schema"
$schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
type: object
properties:
  foo:
    type: string"""
    path = tmp_path / "custom_schema.yaml"
    with path.open("w") as f:
        f.write(contents)
    return path


@pytest.fixture()
def bad_blocks_file_path(tmp_path):
    to_replace = b"REPLACE"
    replacement = b"ABCDEFG"
    buff = asdf.dumps({"arr": np.frombuffer(to_replace, np.uint8)})
    buff = buff.replace(to_replace, replacement)
    path = tmp_path / "bad_block.asdf"
    with path.open("wb") as f:
        f.write(buff)
    return path


def test_valid(capsys, valid_file_path):
    assert main.main_from_args(["validate", str(valid_file_path)]) == 0

    captured = capsys.readouterr()
    assert "valid" in captured.out


def test_invalid(invalid_file_path):
    with pytest.raises(asdf.ValidationError):
        main.main_from_args(["validate", str(invalid_file_path)])


def test_custom_schema(valid_file_path, custom_schema_path):
    with pytest.raises(asdf.ValidationError):
        main.main_from_args(["validate", str(valid_file_path), "--custom_schema", str(custom_schema_path)])


def test_block_checksum(bad_blocks_file_path):
    with pytest.raises(ValueError, match="does not match given checksum"):
        main.main_from_args(["validate", str(bad_blocks_file_path)])


def test_skip_checksums(bad_blocks_file_path):
    assert main.main_from_args(["validate", str(bad_blocks_file_path), "--skip_checksums"]) == 0
