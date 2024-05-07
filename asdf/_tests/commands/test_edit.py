import os
import re
from contextlib import contextmanager

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import asdf
from asdf import constants
from asdf._block import io as bio
from asdf.commands import main

RNG = np.random.default_rng(42)


@pytest.fixture(params=asdf.versioning.supported_versions)
def version(request):
    return request.param


@pytest.fixture()
def create_editor(tmp_path):
    """
    Fixture providing a function that generates an editor script.
    """

    def _create_editor(pattern, replacement):
        if isinstance(pattern, str):
            pattern = pattern.encode("utf-8")
        if isinstance(replacement, str):
            replacement = replacement.encode("utf-8")

        editor_path = tmp_path / "editor.py"

        content = f"""import re
import sys

with open(sys.argv[1], "rb") as file:
    content = file.read()

content = re.sub({pattern!r}, {replacement!r}, content, flags=(re.DOTALL | re.MULTILINE))

with open(sys.argv[1], "wb") as file:
    file.write(content)
"""

        with editor_path.open("w") as file:
            file.write(content)

        return f"python3 {editor_path}"

    return _create_editor


@contextmanager
def file_not_modified(path):
    """
    Assert that a file was not modified during the context.
    """
    original_mtime = os.stat(path).st_mtime_ns

    yield

    assert os.stat(path).st_mtime_ns == original_mtime


@pytest.fixture()
def mock_input(monkeypatch):
    """
    Fixture providing a function that mocks the edit module's
    built-in input function.
    """

    @contextmanager
    def _mock_input(pattern, response):
        called = False

        def _input(prompt=None):
            nonlocal called
            called = True
            assert prompt is not None
            assert re.match(pattern, prompt)
            return response

        with monkeypatch.context() as m:
            m.setattr("builtins.input", _input)
            yield

        assert called, "input was not called as expected"

    return _mock_input


@pytest.fixture(autouse=True)
def _default_mock_input(monkeypatch):
    """
    Fixture that raises an error when the program
    requests unexpected input.
    """

    def _input(prompt=None):
        msg = f"Received unexpected request for input: {prompt}"
        raise AssertionError(msg)

    monkeypatch.setattr("builtins.input", _input)


def test_no_blocks(tmp_path, create_editor, version):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"foo: bar", "foo: baz")

    assert main.main_from_args(["edit", file_path]) == 0

    with asdf.open(file_path) as af:
        assert af["foo"] == "baz"


def test_no_blocks_increase_size(tmp_path, create_editor, version):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    new_value = "a" * 32768
    os.environ["EDITOR"] = create_editor(r"foo: bar", f"foo: {new_value}")

    # With no blocks, we can expand the existing file, so this case
    # shouldn't require confirmation from the user.
    assert main.main_from_args(["edit", file_path]) == 0

    with asdf.open(file_path) as af:
        assert af["foo"] == new_value


def test_no_blocks_decrease_size(tmp_path, create_editor, version):
    file_path = str(tmp_path / "test.asdf")

    original_value = "a" * 32768

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = original_value
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(f"foo: {original_value}", "foo: bar")

    assert main.main_from_args(["edit", file_path]) == 0

    with asdf.open(file_path) as af:
        assert af["foo"] == "bar"


def confirm_valid_block_index(file_path):
    # make sure the block index is valid
    with asdf.generic_io.get_file(file_path, "r") as f:
        block_index_offset = bio.find_block_index(f)
        assert block_index_offset is not None
        block_index = bio.read_block_index(f, block_index_offset)
        for block_offset in block_index:
            f.seek(block_offset)
            assert f.read(len(constants.BLOCK_MAGIC)) == constants.BLOCK_MAGIC


def test_with_blocks(tmp_path, create_editor, version):
    file_path = str(tmp_path / "test.asdf")

    array1 = RNG.normal(size=100)
    array2 = RNG.normal(size=100)
    with asdf.AsdfFile(version=version) as af:
        af["array1"] = array1
        af["array2"] = array2
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"foo: bar", "foo: baz")

    assert main.main_from_args(["edit", file_path]) == 0

    with asdf.open(file_path) as af:
        assert af["foo"] == "baz"
        assert_array_equal(af["array1"], array1)
        assert_array_equal(af["array2"], array2)

    confirm_valid_block_index(file_path)


def test_with_blocks_increase_size(tmp_path, create_editor, version, mock_input):
    file_path = str(tmp_path / "test.asdf")

    array1 = RNG.normal(size=100)
    array2 = RNG.normal(size=100)
    with asdf.AsdfFile(version=version) as af:
        af["array1"] = array1
        af["array2"] = array2
        af["foo"] = "bar"
        af.write_to(file_path)

    new_value = "a" * 32768
    os.environ["EDITOR"] = create_editor(r"foo: bar", f"foo: {new_value}")

    # Abort without updating the file
    with mock_input(r"\(c\)ontinue or \(a\)bort\?", "a"), file_not_modified(file_path):
        assert main.main_from_args(["edit", file_path]) == 1

    # Agree to allow the file to be rewritten
    with mock_input(r"\(c\)ontinue or \(a\)bort\?", "c"):
        assert main.main_from_args(["edit", file_path]) == 0

    with asdf.open(file_path) as af:
        assert af["foo"] == new_value
        assert_array_equal(af["array1"], array1)
        assert_array_equal(af["array2"], array2)

    confirm_valid_block_index(file_path)


def test_with_blocks_decrease_size(tmp_path, create_editor, version):
    file_path = str(tmp_path / "test.asdf")

    original_value = "a" * 32768

    array1 = RNG.normal(size=100)
    array2 = RNG.normal(size=100)
    with asdf.AsdfFile(version=version) as af:
        af["array1"] = array1
        af["array2"] = array2
        af["foo"] = original_value
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(f"foo: {original_value}", "foo: bar")

    assert main.main_from_args(["edit", file_path]) == 0

    with asdf.open(file_path) as af:
        assert af["foo"] == "bar"
        assert_array_equal(af["array1"], array1)
        assert_array_equal(af["array2"], array2)

    confirm_valid_block_index(file_path)


def test_no_changes(tmp_path, create_editor, version):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"non-existent-string", "non-existent-string")

    with file_not_modified(file_path):
        assert main.main_from_args(["edit", file_path]) == 0


def test_update_asdf_standard_version(tmp_path, create_editor, version, mock_input):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"^#ASDF_STANDARD .*?$", "#ASDF_STANDARD 999.999.999")

    with file_not_modified(file_path), mock_input(r"\(c\)ontinue editing or \(a\)bort\?", "a"):
        assert main.main_from_args(["edit", file_path]) == 1


def test_update_yaml_version(tmp_path, create_editor, version, mock_input):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"^%YAML 1.1$", "%YAML 1.2")

    with file_not_modified(file_path), mock_input(r"\(c\)ontinue editing or \(a\)bort\?", "a"):
        assert main.main_from_args(["edit", file_path]) == 1


def test_bad_yaml(tmp_path, create_editor, version, mock_input):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"foo: bar", "foo: [")

    with file_not_modified(file_path), mock_input(r"\(c\)ontinue editing or \(a\)bort\?", "a"):
        assert main.main_from_args(["edit", file_path]) == 1


def test_validation_failure(tmp_path, create_editor, version, mock_input):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["array"] = np.arange(100)
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"byteorder: .*?$", "byteorder: med")

    with file_not_modified(file_path), mock_input(r"\(c\)ontinue editing, \(f\)orce update, or \(a\)bort\?", "a"):
        assert main.main_from_args(["edit", file_path]) == 1

    with mock_input(r"\(c\)ontinue editing, \(f\)orce update, or \(a\)bort\?", "f"):
        assert main.main_from_args(["edit", file_path]) == 0

    with open(file_path, "rb") as f:
        content = f.read()
        assert b"byteorder: med" in content


def test_asdf_open_failure(tmp_path, create_editor, version, mock_input):
    file_path = str(tmp_path / "test.asdf")

    with asdf.AsdfFile(version=version) as af:
        af["foo"] = "bar"
        af.write_to(file_path)

    os.environ["EDITOR"] = create_editor(r"^#ASDF .*?$", "#HJKL 1.0.0")

    with file_not_modified(file_path), mock_input(r"\(c\)ontinue editing or \(a\)bort\?", "a"):
        assert main.main_from_args(["edit", file_path]) == 1


def test_non_asdf_file(tmp_path):
    file_path = str(tmp_path / "test.asdf")

    with open(file_path, "w") as f:
        f.write("Dear diary...")

    with file_not_modified(file_path):
        assert main.main_from_args(["edit", file_path]) == 1
