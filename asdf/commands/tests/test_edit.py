import os
import re

import numpy as np
import pytest

import asdf
from asdf.commands import main


def _create_base_asdf_stream(version, oname):
    # Store the data in an arbitrarily nested dictionary
    tree = {
        "foo": 42,
        "name": "Monty",
        "my_stream": asdf.Stream([128], np.float64),
    }
    af = asdf.AsdfFile(tree)
    with open(oname, "wb") as fd:
        af.write_to(fd)
        for k in range(5):
            fd.write(np.array([k] * 128, np.float64).tobytes())


def _create_base_asdf(version, oname):
    """
    In the test temp directory, create a base ASDF file to edit
    and test against.
    """
    seq = np.arange(713)

    # Store the data in an arbitrarily nested dictionary
    tree = {
        "foo": 42,
        "name": "Monty",
        "sequence": seq,
    }

    with asdf.AsdfFile(tree, version=version) as af:
        af.write_to(oname)


def _create_base_asdf_no_blocks(version, oname):
    tree = {
        "foo": 42,
        "name": "Monty",
    }

    with asdf.AsdfFile(tree, version=version) as af:
        af.write_to(oname)


def _create_edited_yaml(base_yaml, edited_yaml, pattern, replacement):
    with open(base_yaml, "rb") as fd:
        content = fd.read()
        new_content = re.sub(pattern, replacement, content)
        with open(edited_yaml, "wb") as fd:
            fd.write(new_content)


def _initialize_test(tmpdir, version, create_asdf):
    asdf_base = os.path.join(tmpdir, "base.asdf")
    yaml_base = os.path.join(tmpdir, "base.yaml")
    asdf_edit = os.path.join(tmpdir, "edit.asdf")
    yaml_edit = os.path.join(tmpdir, "edit.yaml")

    create_asdf(version, asdf_base)
    create_asdf(version, asdf_edit)

    args = ["edit", "-e", "-f", f"{asdf_base}", "-o", f"{yaml_base}"]
    main.main_from_args(args)

    return asdf_base, yaml_base, asdf_edit, yaml_edit


# --------------- Tests ---------------
@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_tack_s_bad_args_bad_f(tmpdir, version):
    asdf_base = os.path.join(tmpdir, "base.asdf")

    args = ["edit", "-e", "-f", f"{asdf_base}", "-o", f"{asdf_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 1


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_tack_s_bad_args_bad_o(tmpdir, version):
    yaml_base = os.path.join(tmpdir, "base.yaml")

    args = ["edit", "-e", "-f", f"{yaml_base}", "-o", f"{yaml_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 1


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_tack_e_bad_args_bad_o(tmpdir, version):
    asdf_base = os.path.join(tmpdir, "base.asdf")

    args = ["edit", "-e", "-f", f"{asdf_base}", "-o", f"{asdf_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 1


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_tack_e_bad_args_bad_f(tmpdir, version):
    yaml_base = os.path.join(tmpdir, "base.yaml")

    args = ["edit", "-e", "-f", f"{yaml_base}", "-o", f"{yaml_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 1


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_bad_args(tmpdir, version):
    asdf_base = os.path.join(tmpdir, "base.asdf")

    args = ["edit", "-e", "-f", f"{asdf_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 2


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_save_to_no_binary(tmpdir, version):
    asdf_base = os.path.join(tmpdir, "base.asdf")
    yaml_base = os.path.join(tmpdir, "base.yaml")
    yaml_edit = os.path.join(tmpdir, "edit.yaml")

    _create_base_asdf_no_blocks(version, asdf_base)
    _create_base_asdf_no_blocks(version, yaml_base)

    _create_edited_yaml(yaml_base, yaml_edit, b"foo: 42", b"foo: 2")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 1


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_no_binary(tmpdir, version):
    asdf_base = os.path.join(tmpdir, "base.asdf")
    yaml_base = os.path.join(tmpdir, "base.yaml")
    _create_base_asdf_no_blocks(version, asdf_base)

    args = ["edit", "-e", "-f", f"{asdf_base}", "-o", f"{yaml_base}"]
    with pytest.raises(SystemExit) as e:
        main.main(args)
    assert e.value.code == 1


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_smaller(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(
        tmpdir, version, _create_base_asdf
    )

    _create_edited_yaml(yaml_base, yaml_edit, b"foo: 42", b"foo: 2")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    main.main_from_args(args)
    assert os.path.getsize(asdf_edit) == os.path.getsize(asdf_base)

    with asdf.open(asdf_edit) as af:
        assert af.tree["foo"] == 2


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_equal(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(
        tmpdir, version, _create_base_asdf
    )

    _create_edited_yaml(yaml_base, yaml_edit, b"foo: 42", b"foo: 41")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    main.main_from_args(args)
    assert os.path.getsize(asdf_edit) == os.path.getsize(asdf_base)

    with asdf.open(asdf_edit) as af:
        assert af.tree["foo"] == 41


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_larger(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(
        tmpdir, version, _create_base_asdf
    )

    _create_edited_yaml(yaml_base, yaml_edit, b"foo: 42", b"foo: 42\nbar: 13")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    main.main_from_args(args)
    assert os.path.getsize(asdf_edit) - os.path.getsize(asdf_base) > 10000

    with asdf.open(asdf_edit) as af:
        assert "bar" in af.tree
        assert af.tree["bar"] == 13


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_edit_larger_stream(tmpdir, version):
    asdf_base, yaml_base, asdf_edit, yaml_edit = _initialize_test(
        tmpdir, version, _create_base_asdf_stream
    )

    _create_edited_yaml(yaml_base, yaml_edit, b"foo: 42", b"foo: 42\nbar: 13")

    args = ["edit", "-s", "-f", f"{yaml_edit}", "-o", f"{asdf_edit}"]
    main.main_from_args(args)
    assert os.path.getsize(asdf_edit) - os.path.getsize(asdf_base) > 10000

    with asdf.open(asdf_edit) as af:
        assert "bar" in af.tree
        assert af.tree["bar"] == 13
